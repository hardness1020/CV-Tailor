"""
Management command to seed realistic demo data for screenshots and demos.

Creates pre-enriched artifacts, generations with bullet points, and export jobs
WITHOUT requiring any LLM API calls. All enrichment data is hardcoded.

Usage:
    docker compose exec backend uv run python manage.py seed_demo_data
    docker compose exec backend uv run python manage.py seed_demo_data --reset
"""

import hashlib
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from artifacts.models import Artifact, Evidence
from export.models import ExportJob, ExportTemplate
from generation.models import (
    BulletGenerationJob,
    BulletPoint,
    CVTemplate,
    GeneratedDocument,
    JobDescription,
)

User = get_user_model()

DEMO_EMAIL = "demo@cvtailor.dev"
DEMO_PASSWORD = "demo1234"


# ── Artifact seed data ─────────────────────────────────────────────

ARTIFACTS = [
    {
        "title": "E-Commerce Platform Migration",
        "description": (
            "Led the migration of a monolithic e-commerce platform serving "
            "2M+ monthly users from a legacy PHP stack to a microservices "
            "architecture using Python, Django, and React. Reduced page load "
            "times by 60% and deployment frequency from bi-weekly to daily."
        ),
        "artifact_type": "project",
        "start_date": date(2024, 3, 1),
        "end_date": date(2024, 11, 15),
        "technologies": ["Python", "Django", "React", "PostgreSQL", "Redis", "Docker", "AWS ECS"],
        "status": "complete",
        "last_wizard_step": 6,
        "processing_confidence": 0.92,
        "unified_description": (
            "Spearheaded a full-stack migration of a high-traffic e-commerce "
            "platform from monolithic PHP to microservices. Designed and "
            "implemented 12 domain-bounded services with event-driven "
            "communication via Redis Streams. Established CI/CD pipelines "
            "achieving 99.9% deployment success rate. Migrated 4TB of "
            "production data with zero downtime using a dual-write strategy."
        ),
        "enriched_technologies": [
            "Python 3.11", "Django 4.2", "Django REST Framework",
            "React 18", "TypeScript", "PostgreSQL 15", "Redis 7",
            "Docker", "AWS ECS Fargate", "Terraform", "GitHub Actions",
        ],
        "enriched_achievements": [
            {"text": "Reduced page load times by 60% through service decomposition", "metric": "60%"},
            {"text": "Migrated 4TB production data with zero downtime", "metric": "4TB"},
            {"text": "Increased deployment frequency from bi-weekly to daily releases", "metric": "14x"},
            {"text": "Achieved 99.9% deployment success rate via CI/CD automation", "metric": "99.9%"},
        ],
        "evidence": [
            {
                "url": "https://github.com/demo-user/ecommerce-platform",
                "evidence_type": "github",
                "description": "Main platform repository",
            },
        ],
    },
    {
        "title": "Real-Time Analytics Dashboard",
        "description": (
            "Built an internal analytics dashboard that processes 500K+ "
            "events per minute using WebSocket streaming. Provides real-time "
            "KPI monitoring, anomaly detection, and customizable alerting "
            "for the product and engineering teams."
        ),
        "artifact_type": "project",
        "start_date": date(2024, 6, 1),
        "end_date": date(2024, 9, 30),
        "technologies": ["React", "TypeScript", "D3.js", "WebSocket", "FastAPI", "ClickHouse"],
        "status": "complete",
        "last_wizard_step": 6,
        "processing_confidence": 0.88,
        "unified_description": (
            "Designed and developed a real-time analytics dashboard serving "
            "50+ internal stakeholders. Implemented WebSocket-based streaming "
            "pipeline processing 500K+ events/minute with sub-second latency. "
            "Built interactive D3.js visualizations with drill-down "
            "capabilities. Integrated ML-based anomaly detection that "
            "reduced incident response time by 45%."
        ),
        "enriched_technologies": [
            "React 18", "TypeScript 5", "D3.js", "Recharts",
            "WebSocket", "FastAPI", "ClickHouse", "Apache Kafka",
            "Python", "scikit-learn", "Docker Compose",
        ],
        "enriched_achievements": [
            {"text": "Processes 500K+ events per minute with sub-second latency", "metric": "500K/min"},
            {"text": "Reduced incident response time by 45% with anomaly detection", "metric": "45%"},
            {"text": "Serves 50+ internal stakeholders across 3 departments", "metric": "50+"},
        ],
        "evidence": [
            {
                "url": "https://github.com/demo-user/analytics-dashboard",
                "evidence_type": "github",
                "description": "Dashboard frontend and API",
            },
        ],
    },
    {
        "title": "Open Source CLI Tool — docgen",
        "description": (
            "Created and maintain an open-source CLI tool that auto-generates "
            "API documentation from Python source code. 1.2K GitHub stars, "
            "published on PyPI with 15K+ monthly downloads."
        ),
        "artifact_type": "project",
        "start_date": date(2023, 9, 1),
        "end_date": None,
        "technologies": ["Python", "Click", "Jinja2", "AST", "PyPI"],
        "status": "complete",
        "last_wizard_step": 6,
        "processing_confidence": 0.95,
        "unified_description": (
            "Built and actively maintain docgen, an open-source CLI tool for "
            "automated API documentation generation from Python source. Uses "
            "AST parsing for accurate type extraction and Jinja2 templates "
            "for customizable output formats (Markdown, HTML, RST). Published "
            "on PyPI with automated release pipeline. Community-driven "
            "development with 30+ contributors."
        ),
        "enriched_technologies": [
            "Python 3.10+", "Click", "Jinja2", "AST module",
            "PyPI", "GitHub Actions", "pytest", "tox",
            "Sphinx", "Markdown",
        ],
        "enriched_achievements": [
            {"text": "Gained 1.2K GitHub stars and 30+ contributors", "metric": "1.2K stars"},
            {"text": "15K+ monthly downloads on PyPI", "metric": "15K/month"},
            {"text": "Supports 3 output formats: Markdown, HTML, RST", "metric": "3 formats"},
        ],
        "evidence": [
            {
                "url": "https://github.com/demo-user/docgen",
                "evidence_type": "github",
                "description": "Open-source repository",
            },
        ],
    },
    {
        "title": "Senior Software Engineer — Acme Corp",
        "description": (
            "Led a team of 6 engineers building the core payments platform "
            "processing $2B+ in annual transactions. Owned the billing "
            "service, subscription management, and PCI-DSS compliance."
        ),
        "artifact_type": "experience",
        "start_date": date(2022, 1, 15),
        "end_date": date(2024, 2, 28),
        "technologies": ["Python", "Go", "gRPC", "PostgreSQL", "Stripe API", "Kubernetes"],
        "status": "complete",
        "last_wizard_step": 6,
        "processing_confidence": 0.90,
        "unified_description": (
            "Served as Senior Software Engineer and tech lead for the "
            "payments team at Acme Corp. Architected and maintained the "
            "billing microservice handling $2B+ in annual transactions. "
            "Led PCI-DSS Level 1 compliance certification. Mentored 3 "
            "junior engineers through structured growth plans. Reduced "
            "payment processing errors by 78% through idempotency patterns."
        ),
        "enriched_technologies": [
            "Python", "Go", "gRPC", "PostgreSQL", "Redis",
            "Stripe API", "Kubernetes", "Helm", "Datadog",
            "PagerDuty", "Terraform",
        ],
        "enriched_achievements": [
            {"text": "Processed $2B+ in annual transactions with 99.99% uptime", "metric": "$2B+"},
            {"text": "Reduced payment processing errors by 78%", "metric": "78%"},
            {"text": "Led PCI-DSS Level 1 compliance certification", "metric": "Level 1"},
            {"text": "Mentored 3 junior engineers with structured growth plans", "metric": "3 engineers"},
        ],
        "evidence": [],
    },
    {
        "title": "Machine Learning Pipeline for Fraud Detection",
        "description": (
            "Designed and deployed a real-time ML pipeline for transaction "
            "fraud detection. Reduced false positive rate by 35% while "
            "maintaining 99.2% recall on fraudulent transactions."
        ),
        "artifact_type": "project",
        "start_date": date(2023, 4, 1),
        "end_date": date(2023, 12, 15),
        "technologies": ["Python", "scikit-learn", "XGBoost", "Apache Airflow", "MLflow", "AWS SageMaker"],
        "status": "complete",
        "last_wizard_step": 6,
        "processing_confidence": 0.87,
        "unified_description": (
            "Designed, trained, and deployed a real-time fraud detection ML "
            "pipeline processing 10K+ transactions per second. Built feature "
            "engineering pipeline with 200+ signals. Implemented model "
            "versioning with MLflow and automated retraining via Airflow. "
            "Deployed on AWS SageMaker with A/B testing for model rollouts."
        ),
        "enriched_technologies": [
            "Python", "scikit-learn", "XGBoost", "LightGBM",
            "Apache Airflow", "MLflow", "AWS SageMaker",
            "Pandas", "NumPy", "Docker", "PostgreSQL",
        ],
        "enriched_achievements": [
            {"text": "Reduced false positive rate by 35% while maintaining 99.2% recall", "metric": "35%"},
            {"text": "Processes 10K+ transactions per second in real-time", "metric": "10K TPS"},
            {"text": "Built feature engineering pipeline with 200+ signals", "metric": "200+ signals"},
        ],
        "evidence": [
            {
                "url": "https://github.com/demo-user/fraud-detection-pipeline",
                "evidence_type": "github",
                "description": "ML pipeline repository",
            },
        ],
    },
]


# ── Job description seed data ──────────────────────────────────────

JOB_DESCRIPTIONS = [
    {
        "raw_content": (
            "Senior Full-Stack Engineer — TechCorp\n\n"
            "We're looking for a Senior Full-Stack Engineer to join our "
            "platform team. You'll design and build scalable web applications "
            "serving millions of users.\n\n"
            "Requirements:\n"
            "- 5+ years experience with Python and modern JavaScript/TypeScript\n"
            "- Strong experience with Django or FastAPI\n"
            "- React or Vue.js frontend experience\n"
            "- PostgreSQL and Redis expertise\n"
            "- Experience with Docker, Kubernetes, and CI/CD pipelines\n"
            "- Track record of leading technical projects\n\n"
            "Nice to have:\n"
            "- Open source contributions\n"
            "- Experience with microservices architecture\n"
            "- Machine learning or data pipeline experience"
        ),
        "company_name": "TechCorp",
        "role_title": "Senior Full-Stack Engineer",
        "parsing_confidence": 0.91,
        "parsed_data": {
            "key_requirements": [
                "Python", "TypeScript", "Django", "React",
                "PostgreSQL", "Redis", "Docker", "Kubernetes", "CI/CD",
            ],
            "experience_years": 5,
            "seniority": "senior",
        },
    },
    {
        "raw_content": (
            "Staff Software Engineer, Data Platform — DataScale Inc.\n\n"
            "Join our data platform team building the infrastructure that "
            "powers real-time analytics for Fortune 500 clients.\n\n"
            "Requirements:\n"
            "- 7+ years of software engineering experience\n"
            "- Deep expertise in Python and distributed systems\n"
            "- Experience with streaming data (Kafka, Kinesis, or similar)\n"
            "- Strong SQL and data modeling skills\n"
            "- Experience with ML pipelines and model deployment\n"
            "- Leadership experience mentoring engineers"
        ),
        "company_name": "DataScale Inc.",
        "role_title": "Staff Software Engineer, Data Platform",
        "parsing_confidence": 0.88,
        "parsed_data": {
            "key_requirements": [
                "Python", "distributed systems", "Kafka",
                "SQL", "ML pipelines", "mentoring",
            ],
            "experience_years": 7,
            "seniority": "staff",
        },
    },
]


# ── Bullet points per artifact per generation ──────────────────────

# Keyed by (artifact_index, generation_index) → list of 3 bullets
BULLETS = {
    (0, 0): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Led migration of 2M-user e-commerce platform from monolithic PHP to Python microservices architecture",
            "keywords": ["migration", "microservices", "Python", "e-commerce"],
            "metrics": {"users": "2M+", "services": "12"},
            "confidence_score": 0.93, "quality_score": 0.91,
            "has_action_verb": True, "keyword_relevance_score": 0.88,
            "user_approved": True,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Designed 12 domain-bounded microservices with event-driven communication via Redis Streams and gRPC",
            "keywords": ["microservices", "Redis", "gRPC", "event-driven"],
            "metrics": {"services": "12"},
            "confidence_score": 0.90, "quality_score": 0.88,
            "has_action_verb": True, "keyword_relevance_score": 0.85,
            "user_approved": True,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Reduced page load times by 60% and increased deployment frequency from bi-weekly to daily releases",
            "keywords": ["performance", "deployment", "CI/CD"],
            "metrics": {"load_time_reduction": "60%", "deployment_frequency": "14x"},
            "confidence_score": 0.95, "quality_score": 0.94,
            "has_action_verb": True, "keyword_relevance_score": 0.82,
            "user_approved": True,
        },
    ],
    (1, 0): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Built real-time analytics dashboard processing 500K+ events per minute with sub-second streaming latency",
            "keywords": ["analytics", "real-time", "WebSocket", "dashboard"],
            "metrics": {"events_per_minute": "500K+"},
            "confidence_score": 0.91, "quality_score": 0.89,
            "has_action_verb": True, "keyword_relevance_score": 0.86,
            "user_approved": True,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Implemented WebSocket streaming pipeline with D3.js interactive visualizations and drill-down capabilities",
            "keywords": ["WebSocket", "D3.js", "TypeScript", "visualization"],
            "metrics": {},
            "confidence_score": 0.87, "quality_score": 0.85,
            "has_action_verb": True, "keyword_relevance_score": 0.80,
            "user_approved": False,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Reduced incident response time by 45% through ML-based anomaly detection serving 50+ stakeholders",
            "keywords": ["anomaly detection", "ML", "monitoring"],
            "metrics": {"response_time_reduction": "45%", "stakeholders": "50+"},
            "confidence_score": 0.89, "quality_score": 0.87,
            "has_action_verb": True, "keyword_relevance_score": 0.78,
            "user_approved": True,
        },
    ],
    (2, 0): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Created and maintain open-source CLI tool with 1.2K GitHub stars and 15K+ monthly PyPI downloads",
            "keywords": ["open-source", "CLI", "Python", "PyPI"],
            "metrics": {"stars": "1.2K", "downloads": "15K/month"},
            "confidence_score": 0.94, "quality_score": 0.92,
            "has_action_verb": True, "keyword_relevance_score": 0.75,
            "user_approved": True,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Engineered AST-based Python source parser with Jinja2 templates supporting Markdown, HTML, and RST output",
            "keywords": ["AST", "Python", "Jinja2", "documentation"],
            "metrics": {"formats": "3"},
            "confidence_score": 0.88, "quality_score": 0.86,
            "has_action_verb": True, "keyword_relevance_score": 0.72,
            "user_approved": True,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Grew contributor community to 30+ developers through clear documentation and structured onboarding process",
            "keywords": ["open-source", "community", "documentation"],
            "metrics": {"contributors": "30+"},
            "confidence_score": 0.86, "quality_score": 0.84,
            "has_action_verb": True, "keyword_relevance_score": 0.70,
            "user_approved": False,
        },
    ],
    (3, 0): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Led payments team processing $2B+ annually as Senior Engineer and tech lead at a fintech company",
            "keywords": ["payments", "tech lead", "fintech", "leadership"],
            "metrics": {"annual_volume": "$2B+"},
            "confidence_score": 0.92, "quality_score": 0.90,
            "has_action_verb": True, "keyword_relevance_score": 0.84,
            "user_approved": True,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Architected billing microservice with idempotency patterns using Python, Go, gRPC, and Stripe integration",
            "keywords": ["microservice", "Python", "Go", "gRPC", "Stripe"],
            "metrics": {},
            "confidence_score": 0.89, "quality_score": 0.87,
            "has_action_verb": True, "keyword_relevance_score": 0.86,
            "user_approved": True,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Reduced payment processing errors by 78% and led PCI-DSS Level 1 compliance certification process",
            "keywords": ["error reduction", "PCI-DSS", "compliance"],
            "metrics": {"error_reduction": "78%"},
            "confidence_score": 0.91, "quality_score": 0.89,
            "has_action_verb": True, "keyword_relevance_score": 0.80,
            "user_approved": True,
        },
    ],
    (4, 0): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Designed and deployed real-time ML fraud detection pipeline processing 10K+ transactions per second",
            "keywords": ["ML", "fraud detection", "real-time", "pipeline"],
            "metrics": {"tps": "10K+"},
            "confidence_score": 0.90, "quality_score": 0.88,
            "has_action_verb": True, "keyword_relevance_score": 0.83,
            "user_approved": True,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Built feature engineering pipeline with 200+ signals using XGBoost, MLflow, and AWS SageMaker deployment",
            "keywords": ["feature engineering", "XGBoost", "MLflow", "SageMaker"],
            "metrics": {"signals": "200+"},
            "confidence_score": 0.87, "quality_score": 0.85,
            "has_action_verb": True, "keyword_relevance_score": 0.81,
            "user_approved": True,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Reduced false positive rate by 35% while maintaining 99.2% recall on fraudulent transaction detection",
            "keywords": ["false positive", "recall", "fraud detection"],
            "metrics": {"fp_reduction": "35%", "recall": "99.2%"},
            "confidence_score": 0.93, "quality_score": 0.91,
            "has_action_verb": True, "keyword_relevance_score": 0.79,
            "user_approved": True,
        },
    ],
    # Second generation — fewer artifacts (3 of 5)
    (0, 1): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Migrated high-traffic e-commerce platform to microservices, enabling daily deployments for 2M+ users",
            "keywords": ["migration", "microservices", "deployment", "scalability"],
            "metrics": {"users": "2M+"},
            "confidence_score": 0.91, "quality_score": 0.89,
            "has_action_verb": True, "keyword_relevance_score": 0.82,
            "user_approved": False,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Implemented dual-write migration strategy for 4TB production database with zero-downtime data transfer",
            "keywords": ["migration", "database", "zero-downtime", "PostgreSQL"],
            "metrics": {"data_volume": "4TB"},
            "confidence_score": 0.88, "quality_score": 0.86,
            "has_action_verb": True, "keyword_relevance_score": 0.79,
            "user_approved": False,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Achieved 99.9% deployment success rate through automated CI/CD pipelines and comprehensive test coverage",
            "keywords": ["CI/CD", "deployment", "testing", "automation"],
            "metrics": {"success_rate": "99.9%"},
            "confidence_score": 0.90, "quality_score": 0.88,
            "has_action_verb": True, "keyword_relevance_score": 0.85,
            "user_approved": False,
        },
    ],
    (3, 1): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Served as tech lead for payments platform handling $2B+ annually with 99.99% system uptime guarantee",
            "keywords": ["tech lead", "payments", "uptime", "reliability"],
            "metrics": {"volume": "$2B+", "uptime": "99.99%"},
            "confidence_score": 0.92, "quality_score": 0.90,
            "has_action_verb": True, "keyword_relevance_score": 0.87,
            "user_approved": False,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Built distributed billing service using Go and gRPC with Stripe integration and Kubernetes orchestration",
            "keywords": ["Go", "gRPC", "Stripe", "Kubernetes", "distributed"],
            "metrics": {},
            "confidence_score": 0.89, "quality_score": 0.87,
            "has_action_verb": True, "keyword_relevance_score": 0.90,
            "user_approved": False,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Mentored 3 junior engineers through structured growth plans, with all promoted within eighteen months",
            "keywords": ["mentoring", "leadership", "growth", "team"],
            "metrics": {"mentees": "3", "promotion_rate": "100%"},
            "confidence_score": 0.85, "quality_score": 0.83,
            "has_action_verb": True, "keyword_relevance_score": 0.75,
            "user_approved": False,
        },
    ],
    (4, 1): [
        {
            "position": 1, "bullet_type": "achievement",
            "text": "Deployed production ML pipeline for fraud detection processing 10K transactions per second in real-time",
            "keywords": ["ML", "fraud", "real-time", "production"],
            "metrics": {"tps": "10K"},
            "confidence_score": 0.89, "quality_score": 0.87,
            "has_action_verb": True, "keyword_relevance_score": 0.86,
            "user_approved": False,
        },
        {
            "position": 2, "bullet_type": "technical",
            "text": "Implemented model versioning with MLflow and automated retraining pipelines using Apache Airflow scheduler",
            "keywords": ["MLflow", "Airflow", "model versioning", "automation"],
            "metrics": {},
            "confidence_score": 0.86, "quality_score": 0.84,
            "has_action_verb": True, "keyword_relevance_score": 0.82,
            "user_approved": False,
        },
        {
            "position": 3, "bullet_type": "impact",
            "text": "Achieved 35% reduction in false positives while maintaining 99.2% recall, saving $1.2M annually in fraud",
            "keywords": ["false positive", "recall", "cost savings", "fraud"],
            "metrics": {"fp_reduction": "35%", "recall": "99.2%", "savings": "$1.2M"},
            "confidence_score": 0.92, "quality_score": 0.90,
            "has_action_verb": True, "keyword_relevance_score": 0.84,
            "user_approved": False,
        },
    ],
}


class Command(BaseCommand):
    help = "Seed database with realistic demo data for screenshots (no API keys needed)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        user = self._get_or_create_user()
        artifacts = self._create_artifacts(user)
        job_descs = self._create_job_descriptions()
        generations = self._create_generations(user, artifacts, job_descs)
        self._create_bullets(user, artifacts, generations)
        self._create_export(user, generations)
        self._create_templates()

        self.stdout.write(self.style.SUCCESS(
            f"\nDemo data seeded successfully!\n"
            f"  User: {DEMO_EMAIL} / {DEMO_PASSWORD}\n"
            f"  Artifacts: {len(artifacts)}\n"
            f"  Generations: {len(generations)}\n"
            f"  Bullet points: {BulletPoint.objects.filter(cv_generation__user=user).count()}\n"
        ))

    # ── Helpers ─────────────────────────────────────────────────────

    def _reset(self):
        """Remove all demo user data."""
        try:
            user = User.objects.get(email=DEMO_EMAIL)
            # Cascade deletes handle related objects
            user.artifacts.all().delete()
            user.generated_documents.all().delete()
            user.export_jobs.all().delete()
            self.stdout.write(self.style.WARNING("Existing demo data deleted."))
        except User.DoesNotExist:
            pass

    def _get_or_create_user(self):
        user, created = User.objects.get_or_create(
            email=DEMO_EMAIL,
            defaults={
                "username": "demo",
                "first_name": "Alex",
                "last_name": "Chen",
                "bio": "Full-stack engineer with 7+ years building scalable web applications and data pipelines.",
                "location": "San Francisco, CA",
                "linkedin_url": "https://linkedin.com/in/alexchen",
                "github_url": "https://github.com/demo-user",
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stdout.write(f"  Created demo user: {DEMO_EMAIL}")
        else:
            self.stdout.write(f"  Using existing user: {DEMO_EMAIL}")
        return user

    def _create_artifacts(self, user):
        created = []
        for data in ARTIFACTS:
            evidence_data = data.pop("evidence")
            artifact, was_created = Artifact.objects.get_or_create(
                user=user,
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "artifact_type": data["artifact_type"],
                    "start_date": data["start_date"],
                    "end_date": data["end_date"],
                    "technologies": data["technologies"],
                    "status": data["status"],
                    "last_wizard_step": data["last_wizard_step"],
                    "processing_confidence": data["processing_confidence"],
                    "unified_description": data["unified_description"],
                    "enriched_technologies": data["enriched_technologies"],
                    "enriched_achievements": data["enriched_achievements"],
                    "wizard_completed_at": timezone.now() - timedelta(days=len(created)),
                },
            )
            # Restore evidence_data for potential re-runs
            data["evidence"] = evidence_data

            if was_created:
                for ev in evidence_data:
                    Evidence.objects.create(artifact=artifact, **ev)
                self.stdout.write(f"  Created artifact: {artifact.title}")
            else:
                self.stdout.write(f"  Artifact exists: {artifact.title}")

            created.append(artifact)
        return created

    def _create_job_descriptions(self):
        created = []
        for data in JOB_DESCRIPTIONS:
            content_hash = hashlib.sha256(data["raw_content"].encode()).hexdigest()
            jd, _ = JobDescription.objects.get_or_create(
                content_hash=content_hash,
                defaults={
                    "raw_content": data["raw_content"],
                    "company_name": data["company_name"],
                    "role_title": data["role_title"],
                    "parsing_confidence": data["parsing_confidence"],
                    "parsed_data": data["parsed_data"],
                },
            )
            created.append(jd)
            self.stdout.write(f"  Job description: {jd.role_title} at {jd.company_name}")
        return created

    def _create_generations(self, user, artifacts, job_descs):
        generations = []
        now = timezone.now()

        # Generation 1: All 5 artifacts, completed
        gen1_hash = hashlib.sha256(
            JOB_DESCRIPTIONS[0]["raw_content"].encode()
        ).hexdigest()
        gen1, _ = GeneratedDocument.objects.get_or_create(
            user=user,
            job_description_hash=gen1_hash,
            document_type="cv",
            defaults={
                "job_description": job_descs[0],
                "job_description_data": JOB_DESCRIPTIONS[0]["parsed_data"],
                "status": "bullets_ready",
                "progress_percentage": 100,
                "artifacts_used": [a.id for a in artifacts],
                "model_version": "gpt-5-0125",
                "generation_time_ms": 4200,
                "bullets_generated_at": now - timedelta(hours=2),
                "bullets_count": 15,
                "metadata": {
                    "match_score": 0.87,
                    "artifacts_matched": 5,
                    "total_keywords_matched": 12,
                },
            },
        )
        generations.append(gen1)
        self.stdout.write(f"  Generation 1: {gen1.status}")

        # Generation 2: 3 artifacts, completed
        gen2_hash = hashlib.sha256(
            JOB_DESCRIPTIONS[1]["raw_content"].encode()
        ).hexdigest()
        gen2, _ = GeneratedDocument.objects.get_or_create(
            user=user,
            job_description_hash=gen2_hash,
            document_type="cv",
            defaults={
                "job_description": job_descs[1],
                "job_description_data": JOB_DESCRIPTIONS[1]["parsed_data"],
                "status": "completed",
                "progress_percentage": 100,
                "artifacts_used": [artifacts[0].id, artifacts[3].id, artifacts[4].id],
                "model_version": "gpt-5-0125",
                "generation_time_ms": 3800,
                "bullets_generated_at": now - timedelta(days=1),
                "bullets_count": 9,
                "assembled_at": now - timedelta(hours=23),
                "completed_at": now - timedelta(hours=23),
                "metadata": {
                    "match_score": 0.82,
                    "artifacts_matched": 3,
                    "total_keywords_matched": 9,
                },
            },
        )
        generations.append(gen2)
        self.stdout.write(f"  Generation 2: {gen2.status}")

        return generations

    def _create_bullets(self, user, artifacts, generations):
        now = timezone.now()
        count = 0

        for (art_idx, gen_idx), bullets_data in BULLETS.items():
            artifact = artifacts[art_idx]
            generation = generations[gen_idx]

            for bullet_data in bullets_data:
                _, was_created = BulletPoint.objects.get_or_create(
                    artifact=artifact,
                    cv_generation=generation,
                    position=bullet_data["position"],
                    defaults={
                        "bullet_type": bullet_data["bullet_type"],
                        "text": bullet_data["text"],
                        "keywords": bullet_data["keywords"],
                        "metrics": bullet_data["metrics"],
                        "confidence_score": bullet_data["confidence_score"],
                        "quality_score": bullet_data["quality_score"],
                        "has_action_verb": bullet_data["has_action_verb"],
                        "keyword_relevance_score": bullet_data["keyword_relevance_score"],
                        "user_approved": bullet_data["user_approved"],
                        "approved_at": now if bullet_data["user_approved"] else None,
                        # Use approved_by_id to avoid serializer bug (IntegerField
                        # override on BulletPointSerializer can't handle User objects)
                        "approved_by_id": user.id if bullet_data["user_approved"] else None,
                    },
                )
                if was_created:
                    count += 1

        # Create a BulletGenerationJob for each artifact-generation pair
        for gen_idx, generation in enumerate(generations):
            art_indices = [0, 1, 2, 3, 4] if gen_idx == 0 else [0, 3, 4]
            for art_idx in art_indices:
                BulletGenerationJob.objects.get_or_create(
                    artifact=artifacts[art_idx],
                    cv_generation=generation,
                    user=user,
                    defaults={
                        "status": "completed",
                        "progress_percentage": 100,
                        "generation_attempts": 1,
                        "job_context": JOB_DESCRIPTIONS[gen_idx]["parsed_data"],
                        "processing_duration_ms": 1200 + (art_idx * 300),
                        "llm_cost_usd": Decimal("0.0045"),
                        "tokens_used": 1800 + (art_idx * 200),
                        "started_at": now - timedelta(hours=3),
                        "completed_at": now - timedelta(hours=2, minutes=50),
                    },
                )

        self.stdout.write(f"  Created {count} bullet points")

    def _create_export(self, user, generations):
        # Create an export template
        template, _ = ExportTemplate.objects.get_or_create(
            name="Modern Professional",
            defaults={
                "category": "modern",
                "description": "Clean, modern template with accent colors and clear section hierarchy.",
                "template_config": {"accent_color": "#2563eb", "font": "Inter"},
                "css_styles": "",
                "is_active": True,
            },
        )

        # Create a completed export job for the second generation
        ExportJob.objects.get_or_create(
            user=user,
            generated_document=generations[1],
            format="pdf",
            defaults={
                "template": template,
                "status": "completed",
                "progress_percentage": 100,
                "file_path": "exports/demo_cv_techcorp.pdf",
                "file_size": 145_000,
                "download_count": 2,
                "completed_at": timezone.now() - timedelta(hours=22),
                "expires_at": timezone.now() + timedelta(days=7),
            },
        )
        self.stdout.write("  Created export job (PDF)")

    def _create_templates(self):
        templates = [
            ("Modern Professional", "modern", "Clean layout with accent colors and clear hierarchy."),
            ("Classic Academic", "classic", "Traditional format suitable for academic and research roles."),
            ("Technical Engineer", "technical", "Code-friendly template highlighting technical skills."),
        ]
        for name, category, desc in templates:
            CVTemplate.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "description": desc,
                    "template_config": {},
                    "prompt_template": "Generate a professional CV.",
                    "is_active": True,
                },
            )
        self.stdout.write("  Created CV templates")
