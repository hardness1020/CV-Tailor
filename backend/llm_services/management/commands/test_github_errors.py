"""
Django management command to test GitHub error logging.
Usage: python manage.py test_github_errors
"""
import asyncio
from django.core.management.base import BaseCommand
from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent


class Command(BaseCommand):
    help = 'Test GitHub agent error logging with failing repositories'

    def handle(self, *args, **options):
        """Run GitHub error logging tests"""
        asyncio.run(self.run_tests())

    async def run_tests(self):
        """Test GitHub agent with repos that will fail"""
        agent = GitHubRepositoryAgent()

        # Test 1: Repository that likely doesn't exist or is private (404)
        self.stdout.write(self.style.WARNING("\n" + "="*80))
        self.stdout.write(self.style.WARNING("TEST 1: Testing repository (likely 404 error)"))
        self.stdout.write(self.style.WARNING("="*80))
        result = await agent.analyze_repository(
            repo_url="https://github.com/<GITHUB_USER>/example-private-repo",
            user_id=1,
            token_budget=8000
        )
        self.stdout.write(f"Success: {result.success}")
        self.stdout.write(f"Error message: {result.error_message}")
        self.stdout.write(f"Error code: {result.data.get('error', 'N/A')}")

        # Test 2: Invalid URL format
        self.stdout.write(self.style.WARNING("\n" + "="*80))
        self.stdout.write(self.style.WARNING("TEST 2: Invalid URL format"))
        self.stdout.write(self.style.WARNING("="*80))
        result = await agent.analyze_repository(
            repo_url="https://invalid-url.com/repo",
            user_id=1,
            token_budget=8000
        )
        self.stdout.write(f"Success: {result.success}")
        self.stdout.write(f"Error message: {result.error_message}")

        self.stdout.write(self.style.SUCCESS("\n" + "="*80))
        self.stdout.write(self.style.SUCCESS("Tests completed! Check logs above for detailed error messages."))
        self.stdout.write(self.style.SUCCESS("="*80))
