"""
Django management command to diagnose EnhancedEvidence record creation issues.

Usage:
    python manage.py diagnose_enhanced_evidence
    python manage.py diagnose_enhanced_evidence --artifact-id 123
    python manage.py diagnose_enhanced_evidence --evidence-id 456
    python manage.py diagnose_enhanced_evidence --verbose
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from artifacts.models import Artifact, Evidence, ArtifactProcessingJob
from llm_services.models import EnhancedEvidence


class Command(BaseCommand):
    help = 'Diagnose EnhancedEvidence record creation and linking issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--artifact-id',
            type=int,
            help='Check specific artifact by ID',
        )
        parser.add_argument(
            '--evidence-id',
            type=int,
            help='Check specific evidence by ID',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        artifact_id = options.get('artifact_id')
        evidence_id = options.get('evidence_id')
        verbose = options.get('verbose', False)

        self.stdout.write(self.style.SUCCESS('\n=== EnhancedEvidence Diagnostic Report ===\n'))

        if evidence_id:
            self.diagnose_specific_evidence(evidence_id, verbose)
        elif artifact_id:
            self.diagnose_specific_artifact(artifact_id, verbose)
        else:
            self.diagnose_overall_status(verbose)

    def diagnose_overall_status(self, verbose=False):
        """Show overall system status"""

        # Count totals
        total_evidence = Evidence.objects.count()
        total_enhanced = EnhancedEvidence.objects.count()
        evidence_with_enhanced = Evidence.objects.filter(
            enhanced_version__isnull=False
        ).count()
        evidence_without_enhanced = total_evidence - evidence_with_enhanced

        self.stdout.write(self.style.WARNING('📊 Overall Statistics:\n'))
        self.stdout.write(f'  Total Evidence Records: {total_evidence}\n')
        self.stdout.write(f'  Total EnhancedEvidence Records: {total_enhanced}\n')
        self.stdout.write(f'  Evidence WITH EnhancedEvidence: {evidence_with_enhanced}\n')
        self.stdout.write(f'  Evidence WITHOUT EnhancedEvidence: {evidence_without_enhanced}\n')
        coverage = f'{(evidence_with_enhanced/total_evidence*100):.1f}%' if total_evidence > 0 else 'N/A'
        self.stdout.write(f'  Coverage: {coverage}\n')
        self.stdout.write('\n')

        # Recent enrichment jobs
        recent_jobs = ArtifactProcessingJob.objects.order_by('-created_at')[:5]
        if recent_jobs:
            self.stdout.write(self.style.WARNING('📋 Recent Enrichment Jobs:\n'))
            for job in recent_jobs:
                enhanced_count = EnhancedEvidence.objects.filter(
                    evidence__artifact=job.artifact
                ).count()
                self.stdout.write(f'  Job {job.id}: {job.artifact.title[:30]} - {job.status} ({job.progress_percentage}%) - {enhanced_count} enhanced - {job.created_at.strftime("%Y-%m-%d %H:%M")}\n')
            self.stdout.write('\n')

        # Evidence without enhanced versions
        if evidence_without_enhanced > 0:
            self.stdout.write(self.style.ERROR(f'\n⚠️  Found {evidence_without_enhanced} Evidence records without EnhancedEvidence\n'))

            if verbose:
                missing = Evidence.objects.filter(
                    enhanced_version__isnull=True
                ).select_related('artifact')[:10]

                self.stdout.write('\n  First 10 missing:\n')
                for ev in missing:
                    self.stdout.write(f'    #{ev.id} - {ev.evidence_type} - {ev.artifact.title[:30]} - {ev.url[:50]}\n')
        else:
            self.stdout.write(self.style.SUCCESS('✅ All Evidence records have EnhancedEvidence!\n'))

    def diagnose_specific_artifact(self, artifact_id, verbose=False):
        """Diagnose specific artifact"""
        try:
            artifact = Artifact.objects.get(id=artifact_id)
        except Artifact.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Artifact {artifact_id} not found\n'))
            return

        self.stdout.write(self.style.WARNING(f'🔍 Artifact #{artifact_id}: {artifact.title}\n\n'))

        # Enrichment status
        self.stdout.write(self.style.WARNING('📝 Artifact-Level Enrichment:\n'))
        self.stdout.write(f'  Unified Description: {"Yes" if artifact.unified_description else "No"}\n')
        self.stdout.write(f'  Technologies Count: {len(artifact.enriched_technologies or [])}\n')
        self.stdout.write(f'  Achievements Count: {len(artifact.enriched_achievements or [])}\n')
        self.stdout.write(f'  Processing Confidence: {artifact.processing_confidence:.2f}\n')
        self.stdout.write('\n')

        # Evidence sources
        evidence_list = Evidence.objects.filter(artifact=artifact)
        self.stdout.write(self.style.WARNING(f'📎 Evidence Sources ({evidence_list.count()}):\n'))

        for ev in evidence_list:
            has_enhanced = hasattr(ev, 'enhanced_version') and ev.enhanced_version is not None
            enhanced_icon = '✅' if has_enhanced else '❌'
            accessible_icon = '✅' if ev.is_accessible else '❌'
            self.stdout.write(f'  #{ev.id} - {ev.evidence_type} - {ev.url[:40]} - Enhanced:{enhanced_icon} - Accessible:{accessible_icon}\n')
        self.stdout.write('\n')

        # Processing jobs
        jobs = ArtifactProcessingJob.objects.filter(artifact=artifact).order_by('-created_at')
        if jobs:
            self.stdout.write(self.style.WARNING(f'🔧 Processing Jobs ({jobs.count()}):\n'))
            for job in jobs:
                evidence_count = Evidence.objects.filter(artifact=job.artifact).count()
                enhanced_count = EnhancedEvidence.objects.filter(evidence__artifact=job.artifact).count()
                self.stdout.write(f'  Job {str(job.id)[:8]}: {job.status} ({job.progress_percentage}%) - {enhanced_count}/{evidence_count} enhanced - {job.created_at.strftime("%Y-%m-%d %H:%M")}\n')
            self.stdout.write('\n')

            # Check most recent job for enhanced evidence details
            if verbose and jobs:
                latest_job = jobs.first()
                enhanced_list = EnhancedEvidence.objects.filter(evidence__artifact=artifact).select_related('evidence')
                if enhanced_list:
                    self.stdout.write(self.style.WARNING(f'📋 Enhanced Evidence Details (Job {str(latest_job.id)[:8]}):\n'))
                    for enhanced in enhanced_list:
                        url = enhanced.evidence.url[:40] if enhanced.evidence else 'N/A'
                        data_keys = len(enhanced.processed_content.keys()) if enhanced.processed_content else 0
                        accepted_icon = '✅' if enhanced.accepted else '❌'
                        self.stdout.write(f'    {enhanced.content_type} - {url} - Accepted:{accepted_icon} - Conf:{enhanced.processing_confidence:.2f} - Keys:{data_keys}\n')
                    self.stdout.write('\n')

        # Recommendations
        self.stdout.write(self.style.WARNING('💡 Recommendations:\n'))
        missing_enhanced = evidence_list.exclude(enhanced_version__isnull=False).count()
        if missing_enhanced > 0:
            self.stdout.write(f'  - {missing_enhanced} Evidence records need EnhancedEvidence creation\n')
            self.stdout.write(f'  - Run: python manage.py trigger_enrichment --artifact-id {artifact_id}\n')
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ All evidence has enhanced versions!\n'))

    def diagnose_specific_evidence(self, evidence_id, verbose=False):
        """Diagnose specific evidence"""
        try:
            evidence = Evidence.objects.select_related('artifact').get(id=evidence_id)
        except Evidence.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Evidence {evidence_id} not found\n'))
            return

        self.stdout.write(self.style.WARNING(f'🔍 Evidence #{evidence_id}\n\n'))

        # Basic info
        self.stdout.write(self.style.WARNING('📋 Basic Information:\n'))
        self.stdout.write(f'  Artifact: {evidence.artifact.title} (ID: {evidence.artifact.id})\n')
        self.stdout.write(f'  Type: {evidence.evidence_type}\n')
        self.stdout.write(f'  URL: {evidence.url}\n')
        self.stdout.write(f'  Accessible: {"✅" if evidence.is_accessible else "❌"}\n')
        self.stdout.write(f'  Created: {evidence.created_at.strftime("%Y-%m-%d %H:%M")}\n')
        self.stdout.write('\n')

        # Check for EnhancedEvidence
        try:
            enhanced = evidence.enhanced_version
            self.stdout.write(self.style.SUCCESS('✅ EnhancedEvidence EXISTS\n\n'))

            self.stdout.write(self.style.WARNING('📊 Enhanced Evidence Details:\n'))
            self.stdout.write(f'  ID: {str(enhanced.id)}\n')
            self.stdout.write(f'  Title: {enhanced.title}\n')
            self.stdout.write(f'  Content Type: {enhanced.content_type}\n')
            self.stdout.write(f'  Processing Confidence: {enhanced.processing_confidence:.2f}\n')
            self.stdout.write(f'  Raw Content Length: {len(enhanced.raw_content) if enhanced.raw_content else 0}\n')
            self.stdout.write(f'  Processed Content Keys: {len(enhanced.processed_content.keys()) if enhanced.processed_content else 0}\n')
            self.stdout.write(f'  LLM Model Used: {enhanced.llm_model_used or "N/A"}\n')
            self.stdout.write(f'  Created: {enhanced.created_at.strftime("%Y-%m-%d %H:%M")}\n')
            self.stdout.write('\n')

            if verbose and enhanced.processed_content:
                self.stdout.write(self.style.WARNING('📦 Processed Content Structure:\n'))
                for key, value in enhanced.processed_content.items():
                    if isinstance(value, list):
                        self.stdout.write(f'  - {key}: {len(value)} items\n')
                    elif isinstance(value, dict):
                        self.stdout.write(f'  - {key}: {len(value)} keys\n')
                    else:
                        self.stdout.write(f'  - {key}: {type(value).__name__}\n')
                self.stdout.write('\n')

            # Test API endpoint
            self.stdout.write(self.style.WARNING('🔗 API Test:\n'))
            self.stdout.write(f'  Endpoint: GET /v1/llm/enhanced-artifacts/by-evidence/{evidence_id}/\n')
            self.stdout.write(f'  Expected Status: 200 OK\n\n')

        except EnhancedEvidence.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ EnhancedEvidence DOES NOT EXIST\n\n'))

            # Check for processing attempts
            jobs = ArtifactProcessingJob.objects.filter(artifact=evidence.artifact).order_by('-created_at')
            if jobs:
                latest_job = jobs.first()
                self.stdout.write(self.style.WARNING('📋 Latest Processing Job:\n'))
                self.stdout.write(f'  Job ID: {str(latest_job.id)[:8]}\n')
                self.stdout.write(f'  Status: {latest_job.status}\n')
                self.stdout.write(f'  Progress: {latest_job.progress_percentage}%\n')
                if latest_job.error_message:
                    self.stdout.write(f'  Error: {latest_job.error_message}\n')
                self.stdout.write('\n')

                self.stdout.write(self.style.ERROR('⚠️  Enrichment job ran but EnhancedEvidence was not created!\n'))
                self.stdout.write('    This indicates the enrichment service may have failed for this evidence.\n\n')
            else:
                self.stdout.write(self.style.WARNING('⚠️  No processing jobs found for this artifact\n\n'))

            # Recommendations
            self.stdout.write(self.style.WARNING('💡 Recommendations:\n'))
            self.stdout.write(f'  1. Re-run enrichment for artifact {evidence.artifact.id}\n')
            self.stdout.write(f'  2. Check enrichment service logs for errors\n')
            self.stdout.write(f'  3. Verify evidence URL is accessible: {evidence.url}\n')
