"""
Django management command to collect comprehensive test metadata.

Usage: python manage.py collect_test_metadata [--output=test_results.csv]
"""

import csv
import json
import time
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.test.runner import DiscoverRunner
from django.test import TestCase
import unittest


class TestMetadataCollector(unittest.TextTestResult):
    """Custom test result collector that captures detailed metadata"""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = []
        self.current_test_start_time = None

    def startTest(self, test):
        """Called when a test starts"""
        super().startTest(test)
        self.current_test_start_time = time.time()

    def stopTest(self, test):
        """Called when a test completes"""
        super().stopTest(test)

        # Calculate duration
        duration = time.time() - self.current_test_start_time if self.current_test_start_time else 0

        # Extract test information
        test_method = test._testMethodName
        test_class = test.__class__.__name__
        test_module = test.__class__.__module__

        # Convert module path to file path
        file_path = test_module.replace('.', '/') + '.py'

        # Extract tags from test class
        tags = getattr(test.__class__, 'tags', set())
        if hasattr(test, '_tags'):
            tags = test._tags

        # Determine outcome
        test_id = test.id()
        if self.wasSuccessful():
            if test_id in [t[0].id() for t in self.skipped]:
                outcome = 'skipped'
                error_msg = dict(self.skipped).get(test, '')
                error_type = 'Skipped'
            else:
                outcome = 'passed'
                error_msg = ''
                error_type = ''
        elif test_id in [t[0].id() for t in self.failures]:
            outcome = 'failed'
            error_info = dict(self.failures).get(test, '')
            error_msg = str(error_info)[:500] if error_info else ''
            error_type = 'AssertionError'
        elif test_id in [t[0].id() for t in self.errors]:
            outcome = 'error'
            error_info = dict(self.errors).get(test, '')
            error_msg = str(error_info)[:500] if error_info else ''
            error_type = 'Error'
        else:
            outcome = 'unknown'
            error_msg = ''
            error_type = ''

        # Store result
        self.test_results.append({
            'file': file_path,
            'class': test_class,
            'function': test_method,
            'full_name': test_id,
            'tags': ','.join(sorted(tags)) if tags else '',
            'line_number': '',  # Not easily accessible
            'outcome': outcome,
            'duration': round(duration, 3),
            'error_message': error_msg.replace('\n', ' | ').replace(',', ';'),
            'error_type': error_type,
        })

    def addSuccess(self, test):
        """Track successful test"""
        super().addSuccess(test)

    def addError(self, test, err):
        """Track test error"""
        super().addError(test, err)

    def addFailure(self, test, err):
        """Track test failure"""
        super().addFailure(test, err)

    def addSkip(self, test, reason):
        """Track skipped test"""
        super().addSkip(test, reason)


class Command(BaseCommand):
    help = 'Collect comprehensive test metadata and output to CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='test_results.csv',
            help='Output CSV file path'
        )
        parser.add_argument(
            '--tags',
            type=str,
            nargs='+',
            help='Test tags to filter (e.g., fast unit)'
        )
        parser.add_argument(
            '--batch-name',
            type=str,
            default='all',
            help='Name of the test batch being run'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        tags = options.get('tags', [])
        batch_name = options['batch_name']

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Collecting Test Metadata")
        self.stdout.write(f"Batch: {batch_name}")
        self.stdout.write(f"Tags: {', '.join(tags) if tags else 'all'}")
        self.stdout.write(f"Output: {output_file}")
        self.stdout.write(f"{'='*60}\n")

        # Set up test runner
        runner = DiscoverRunner(verbosity=2, keepdb=True, tags=tags)

        # Discover tests
        self.stdout.write("Discovering tests...")
        suite = runner.test_loader.loadTestsFromModule(runner.test_loader.discover('.'))

        # Create custom result collector
        result_collector = TestMetadataCollector(
            stream=self.stdout,
            descriptions=True,
            verbosity=2
        )

        # Run tests with custom collector
        self.stdout.write(f"\nRunning tests...\n")
        start_time = time.time()

        suite.run(result_collector)

        total_time = time.time() - start_time

        # Write results to CSV
        self.write_csv(output_file, result_collector.test_results, batch_name)

        # Print summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✅ Test collection complete!"))
        self.stdout.write(f"Total tests: {len(result_collector.test_results)}")
        self.stdout.write(f"Duration: {total_time:.2f}s")
        self.stdout.write(f"Output: {output_file}")
        self.stdout.write(f"{'='*60}\n")

        # Print outcome summary
        outcomes = {}
        for result in result_collector.test_results:
            outcome = result['outcome']
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        self.stdout.write("\nOutcome Summary:")
        for outcome, count in sorted(outcomes.items()):
            self.stdout.write(f"  {outcome}: {count}")

    def write_csv(self, output_file, results, batch_name):
        """Write results to CSV file"""

        # Add batch name to each result
        for result in results:
            result['batch'] = batch_name

        fieldnames = [
            'file', 'class', 'function', 'full_name', 'tags',
            'line_number', 'outcome', 'duration', 'error_message', 'error_type', 'batch'
        ]

        # Append to file if it exists, otherwise create new
        file_exists = Path(output_file).exists()
        mode = 'a' if file_exists else 'w'

        with open(output_file, mode, newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(results)

        self.stdout.write(f"Wrote {len(results)} test results to {output_file}")
