"""
Management command to diagnose artifact enrichment issues.

Usage:
    python manage.py diagnose_enrichment <artifact_id>
    python manage.py diagnose_enrichment --all  # Check all artifacts

Example:
    python manage.py diagnose_enrichment 123
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from artifacts.models import Artifact, Evidence, ArtifactProcessingJob
from llm_services.models import EnhancedEvidence

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnose enrichment issues for artifacts'

    def add_arguments(self, parser):
        parser.add_argument(
            'artifact_id',
            nargs='?',
            type=int,
            help='ID of the artifact to diagnose'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all artifacts with failed enrichment'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by user email (only with --all)'
        )

    def handle(self, *args, **options):
        artifact_id = options.get('artifact_id')
        check_all = options.get('all')
        user_email = options.get('user')

        if not artifact_id and not check_all:
            raise CommandError('Please provide an artifact_id or use --all flag')

        if artifact_id:
            self.diagnose_artifact(artifact_id)
        else:
            self.diagnose_all_failed(user_email)

    def diagnose_artifact(self, artifact_id):
        """Diagnose a single artifact"""
        try:
            artifact = Artifact.objects.get(id=artifact_id)
        except Artifact.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Artifact {artifact_id} not found'))
            return

        self.stdout.write(f"\n{'=' * 80}")
        self.stdout.write(self.style.SUCCESS(f'ARTIFACT ENRICHMENT DIAGNOSIS - ID: {artifact_id}'))
        self.stdout.write(f"{'=' * 80}\n")

        # Basic info
        self.stdout.write(self.style.HTTP_INFO('Basic Information:'))
        self.stdout.write(f"  Title: {artifact.title}")
        self.stdout.write(f"  Owner: {artifact.user.email}")
        self.stdout.write(f"  Created: {artifact.created_at}")
        self.stdout.write(f"  Updated: {artifact.updated_at}\n")

        # Evidence sources
        evidence_list = Evidence.objects.filter(artifact=artifact)
        evidence_count = evidence_list.count()

        self.stdout.write(self.style.HTTP_INFO(f'Evidence Sources ({evidence_count}):'))
        if evidence_count == 0:
            self.stdout.write(self.style.ERROR('  ❌ NO EVIDENCE SOURCES - Enrichment will fail'))
            self.stdout.write(self.style.WARNING('     → Add at least 1 GitHub repo or upload a file\n'))
        else:
            for evidence in evidence_list:
                status_icon = '✓' if evidence.is_accessible else '✗'
                if evidence.is_accessible:
                    self.stdout.write(self.style.SUCCESS(f"  [{status_icon}] {evidence.evidence_type}: {evidence.url or evidence.file_path}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  [{status_icon}] {evidence.evidence_type}: {evidence.url or evidence.file_path}"))
                if evidence.validation_metadata:
                    self.stdout.write(f"      Validation: {evidence.validation_metadata}")

        # Processing jobs
        jobs = artifact.processing_jobs.order_by('-created_at')
        job_count = jobs.count()

        self.stdout.write(f"\n{self.style.HTTP_INFO(f'Processing Jobs ({job_count}):')} ")
        if job_count == 0:
            self.stdout.write(self.style.WARNING('  No enrichment has been performed yet\n'))
        else:
            latest_job = jobs.first()
            self.stdout.write(f"  Latest Job ID: {latest_job.id}")
            self.stdout.write(f"  Status: {self._format_status(latest_job.status)}")
            self.stdout.write(f"  Created: {latest_job.created_at}")
            self.stdout.write(f"  Completed: {latest_job.completed_at or 'N/A'}")

            if latest_job.error_message:
                self.stdout.write(self.style.ERROR(f"  Error: {latest_job.error_message}\n"))

            # Enrichment metrics
            metadata = latest_job.metadata_extracted or {}
            if metadata:
                self.stdout.write(f"\n{self.style.HTTP_INFO('Enrichment Metrics:')}")
                self.stdout.write(f"  Sources Processed: {metadata.get('sources_processed', 0)}")
                self.stdout.write(f"  Sources Successful: {metadata.get('sources_successful', 0)}")

                confidence = metadata.get('processing_confidence', 0.0)
                confidence_text = self._format_confidence(confidence)
                self.stdout.write(f"  Confidence: {confidence_text}")

                self.stdout.write(f"  Cost: ${metadata.get('total_cost_usd', 0.0):.4f}")
                self.stdout.write(f"  Time: {metadata.get('processing_time_ms', 0)}ms")

                # Quality validation
                self.stdout.write(f"\n{self.style.HTTP_INFO('Quality Validation:')}")
                validation_failed = metadata.get('validation_failed', False)
                if validation_failed:
                    self.stdout.write(self.style.ERROR('  Status: FAILED'))
                else:
                    self.stdout.write(self.style.SUCCESS('  Status: PASSED'))

                quality_score = metadata.get('quality_score', 0.0)
                score_text = self._format_confidence(quality_score)
                self.stdout.write(f"  Quality Score: {score_text}")

                warnings = metadata.get('quality_warnings', [])
                if warnings:
                    self.stdout.write(self.style.WARNING(f"  Warnings ({len(warnings)}):"))
                    for warning in warnings:
                        self.stdout.write(f"    ⚠ {warning}")

                # Enrichment results
                self.stdout.write(f"\n{self.style.HTTP_INFO('Enrichment Results:')}")
                self.stdout.write(f"  Description Length: {metadata.get('unified_description_length', 0)} chars")
                self.stdout.write(f"  Technologies: {metadata.get('technologies_count', 0)}")
                self.stdout.write(f"  Achievements: {metadata.get('achievements_count', 0)}")

            # Source extractions from EnhancedEvidence
            evidence_list = Evidence.objects.filter(artifact=artifact)
            if evidence_list.exists():
                self.stdout.write(f"\n{self.style.HTTP_INFO('Source Extractions:')}")
                for evidence in evidence_list:
                    try:
                        enhanced = evidence.enhanced_version
                        status_icon = '✓'
                        self.stdout.write(self.style.SUCCESS(f"  [{status_icon}] {evidence.url}"))
                        self.stdout.write(f"      Confidence: {enhanced.processing_confidence:.0%}")
                        self.stdout.write(f"      Accepted: {'Yes' if enhanced.accepted else 'No'}")
                    except EnhancedEvidence.DoesNotExist:
                        status_icon = '✗'
                        self.stdout.write(self.style.ERROR(f"  [{status_icon}] {evidence.url}"))
                        self.stdout.write(self.style.ERROR(f"      Error: Extraction failed or not yet processed"))

        # Current artifact state
        self.stdout.write(f"\n{self.style.HTTP_INFO('Current Artifact State:')}")
        has_description = bool(artifact.unified_description)
        desc_icon = '✓' if has_description else '✗'
        if has_description:
            self.stdout.write(self.style.SUCCESS(f"  [{desc_icon}] Unified Description: {len(artifact.unified_description)} chars"))
        else:
            self.stdout.write(self.style.ERROR(f"  [{desc_icon}] Unified Description: {len(artifact.unified_description)} chars"))

        confidence_text = self._format_confidence(artifact.processing_confidence)
        self.stdout.write(f"  Confidence: {confidence_text}")
        self.stdout.write(f"  Technologies: {len(artifact.enriched_technologies)}")
        self.stdout.write(f"  Achievements: {len(artifact.enriched_achievements)}")

        # Recommendations
        self._print_recommendations(artifact, latest_job if job_count > 0 else None)

        self.stdout.write(f"\n{'=' * 80}\n")

    def diagnose_all_failed(self, user_email=None):
        """Diagnose all artifacts with failed enrichment"""
        query = ArtifactProcessingJob.objects.filter(status='failed')

        if user_email:
            query = query.filter(artifact__user__email=user_email)

        failed_jobs = query.select_related('artifact', 'artifact__user').order_by('-created_at')[:20]

        if not failed_jobs.exists():
            self.stdout.write(self.style.SUCCESS('✓ No failed enrichment jobs found'))
            return

        self.stdout.write(f"\n{self.style.HTTP_INFO(f'FAILED ENRICHMENT JOBS (showing up to 20):')} \n")

        for job in failed_jobs:
            artifact = job.artifact
            self.stdout.write(f"  Artifact ID {artifact.id}: {artifact.title}")
            self.stdout.write(f"    Owner: {artifact.user.email}")
            self.stdout.write(f"    Failed: {job.created_at}")
            self.stdout.write(self.style.ERROR(f"    Error: {job.error_message}"))

            metadata = job.metadata_extracted or {}
            evidence_count = Evidence.objects.filter(artifact=artifact).count()
            self.stdout.write(f"    Evidence Sources: {evidence_count}")
            self.stdout.write(f"    Sources Processed: {metadata.get('sources_processed', 0)}")
            self.stdout.write(f"    Confidence: {metadata.get('processing_confidence', 0.0):.0%}\n")

        self.stdout.write(f"\n{self.style.WARNING('Run with specific artifact ID for detailed diagnosis:')}")
        self.stdout.write(f"  python manage.py diagnose_enrichment <artifact_id>\n")

    def _format_status(self, status):
        """Format status with style"""
        if status == 'completed':
            return self.style.SUCCESS(f"✓ {status}")
        elif status == 'failed':
            return self.style.ERROR(f"✗ {status}")
        elif status == 'processing':
            return self.style.WARNING(f"⟳ {status}")
        else:
            return status

    def _format_confidence(self, confidence):
        """Format confidence with color based on threshold"""
        if confidence >= 0.6:
            return self.style.SUCCESS(f"{confidence:.0%}")
        elif confidence >= 0.5:
            return self.style.WARNING(f"{confidence:.0%}")
        else:
            return self.style.ERROR(f"{confidence:.0%}")

    def _print_recommendations(self, artifact, latest_job):
        """Print actionable recommendations"""
        self.stdout.write(f"\n{self.style.HTTP_INFO('Recommendations:')}")

        evidence_count = Evidence.objects.filter(artifact=artifact).count()

        if evidence_count == 0:
            self.stdout.write(self.style.ERROR('  ❌ Add at least 1 evidence source (GitHub repo or file)'))
            return

        if not latest_job:
            self.stdout.write(self.style.WARNING('  → Trigger enrichment: POST /api/v1/artifacts/{id}/enrich/'))
            return

        if latest_job.status == 'failed':
            metadata = latest_job.metadata_extracted or {}

            if metadata.get('sources_processed', 0) == 0:
                self.stdout.write(self.style.ERROR('  ❌ No evidence sources were processed'))
                self.stdout.write(self.style.WARNING('     → Verify evidence sources are accessible'))

            elif metadata.get('sources_successful', 0) == 0:
                self.stdout.write(self.style.ERROR('  ❌ All source extractions failed'))
                self.stdout.write(self.style.WARNING('     → Check if GitHub repos are public'))
                self.stdout.write(self.style.WARNING('     → Verify uploaded files are valid PDFs'))
                self.stdout.write(self.style.WARNING('     → Check backend logs for extraction errors'))

            elif metadata.get('processing_confidence', 0.0) < 0.6:
                self.stdout.write(self.style.ERROR(f"  ❌ Confidence too low ({metadata.get('processing_confidence', 0.0):.0%} < 60%)"))
                self.stdout.write(self.style.WARNING('     → Add more evidence sources'))
                self.stdout.write(self.style.WARNING('     → Ensure GitHub repos have meaningful READMEs'))
                self.stdout.write(self.style.WARNING('     → Upload detailed project documentation'))

            else:
                self.stdout.write(self.style.WARNING('  → Review error message above for specific issue'))
                self.stdout.write(self.style.WARNING('  → Check backend logs: docker-compose logs backend'))

        elif latest_job.status == 'completed':
            metadata = latest_job.metadata_extracted or {}
            warnings = metadata.get('quality_warnings', [])

            if warnings:
                self.stdout.write(self.style.WARNING('  ⚠ Enrichment succeeded with quality warnings'))
                self.stdout.write(self.style.WARNING('     → Consider addressing warnings for better quality'))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ Enrichment completed successfully with no issues'))
