"""
Tests for ArtifactRankingService (SPEC-20250930)
"""

from django.test import TestCase, tag
from llm_services.services.core.artifact_ranking_service import ArtifactRankingService


@tag('medium', 'integration', 'llm_services')
class TestArtifactRankingService(TestCase):
    """Test suite for ArtifactRankingService"""

    async def test_rank_by_keyword_overlap(self):
        """Test keyword-based ranking"""
        service = ArtifactRankingService()

        artifacts = [
            {
                'id': 1,
                'title': 'Django REST API',
                'technologies': ['Python', 'Django', 'PostgreSQL'],
                'enriched_technologies': []
            },
            {
                'id': 2,
                'title': 'React Dashboard',
                'technologies': ['JavaScript', 'React', 'TypeScript'],
                'enriched_technologies': ['Node.js']
            },
            {
                'id': 3,
                'title': 'Full Stack App',
                'technologies': ['Python', 'React', 'Django', 'PostgreSQL'],
                'enriched_technologies': []
            }
        ]

        job_requirements = ['Python', 'Django', 'React', 'PostgreSQL']

        # Test keyword-only ranking
        ranked = await service.rank_artifacts_by_relevance(
            artifacts,
            job_requirements,
            strategy='keyword'
        )

        self.assertEqual(len(ranked), 3)
        # Full stack app should rank highest (has all 4 requirements)
        self.assertEqual(ranked[0]['id'], 3)
        self.assertGreater(ranked[0]['relevance_score'], 0.9)
        self.assertIn('exact_matches', ranked[0])
        self.assertIn('partial_matches', ranked[0])


    async def test_empty_artifacts(self):
        """Test ranking with empty artifact list"""
        service = ArtifactRankingService()

        ranked = await service.rank_artifacts_by_relevance(
            [],
            ['Python', 'Django'],
            strategy='keyword'
        )

        self.assertEqual(ranked, [])

    async def test_no_job_requirements(self):
        """Test ranking with no job requirements"""
        service = ArtifactRankingService()

        artifacts = [
            {'id': 1, 'technologies': ['Python'], 'enriched_technologies': []}
        ]

        ranked = await service.rank_artifacts_by_relevance(
            artifacts,
            [],
            strategy='keyword'
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]['relevance_score'], 0.0)

    async def test_partial_keyword_matching(self):
        """Test partial keyword matching (fuzzy)"""
        service = ArtifactRankingService()

        artifacts = [
            {
                'id': 1,
                'technologies': ['Node.js', 'Express'],
                'enriched_technologies': []
            }
        ]

        job_requirements = ['Node', 'JavaScript']

        ranked = await service.rank_artifacts_by_relevance(
            artifacts,
            job_requirements,
            strategy='keyword'
        )

        self.assertEqual(len(ranked), 1)
        # Should match 'Node' in 'Node.js' as partial match
        self.assertGreater(ranked[0]['relevance_score'], 0.0)
        self.assertGreater(ranked[0]['partial_matches'], 0)



    # --- NEW TESTS FOR ft-007: Keyword-Only Ranking ---

    def test_keyword_ranking_returns_matched_keywords(self):
        """Test that keyword ranking returns list of matched keywords (ft-007)"""
        service = ArtifactRankingService()

        artifacts = [
            {
                'id': 1,
                'title': 'E-commerce Platform',
                'technologies': ['React', 'Node.js', 'PostgreSQL', 'Redis'],
                'enriched_technologies': []
            }
        ]

        job_requirements = ['React', 'Node.js', 'PostgreSQL']

        ranked = service._rank_by_keyword_overlap(artifacts, job_requirements)

        self.assertEqual(len(ranked), 1)
        self.assertIn('matched_keywords', ranked[0])
        self.assertEqual(set(ranked[0]['matched_keywords']), {'React', 'Node.js', 'PostgreSQL'})

    def test_keyword_ranking_with_fuzzy_matching(self):
        """Test fuzzy matching for typos and abbreviations (ft-007)"""
        service = ArtifactRankingService()

        artifacts = [
            {
                'id': 1,
                'technologies': ['JavaScript', 'TypeScript', 'React'],
                'enriched_technologies': []
            }
        ]

        # Typo: "Reactjs" should fuzzy match "React"
        # Abbreviation: "JS" should fuzzy match "JavaScript"
        job_requirements = ['Reactjs', 'JS', 'TypeScript']

        ranked = service._rank_by_keyword_overlap(artifacts, job_requirements)

        self.assertEqual(len(ranked), 1)
        # Should have some fuzzy matches
        self.assertGreater(ranked[0]['relevance_score'], 0.0)
        # Exact match on TypeScript + fuzzy matches
        self.assertIn('fuzzy_matches', ranked[0])

    def test_keyword_ranking_with_recency_weighting(self):
        """Test recency weighting for recent artifacts (ft-007)"""
        from datetime import date, timedelta
        service = ArtifactRankingService()

        today = date.today()
        one_year_ago = today - timedelta(days=365)

        artifacts = [
            {
                'id': 1,
                'title': 'Old Project',
                'technologies': ['Python', 'Django'],
                'enriched_technologies': [],
                'end_date': one_year_ago.isoformat()  # Old
            },
            {
                'id': 2,
                'title': 'Recent Project',
                'technologies': ['Python', 'Django'],
                'enriched_technologies': [],
                'end_date': today.isoformat()  # Recent
            }
        ]

        job_requirements = ['Python', 'Django']

        ranked = service._rank_by_keyword_overlap(artifacts, job_requirements)

        self.assertEqual(len(ranked), 2)
        # Recent project should rank higher (same keywords but recency boost)
        self.assertEqual(ranked[0]['id'], 2)
        # When both have perfect keyword matches (score=1.0), recency_boost is used as tiebreaker
        self.assertGreater(ranked[0]['recency_boost'], ranked[1]['recency_boost'])

    def test_ranking_scores_normalized_to_0_1(self):
        """Test all relevance scores are between 0.0 and 1.0 (ft-007)"""
        service = ArtifactRankingService()

        artifacts = [
            {'id': 1, 'technologies': ['Python', 'Django', 'React', 'Node.js', 'PostgreSQL'], 'enriched_technologies': []},
            {'id': 2, 'technologies': ['Java'], 'enriched_technologies': []},
            {'id': 3, 'technologies': [], 'enriched_technologies': []},
        ]

        job_requirements = ['Python', 'Django']

        ranked = service._rank_by_keyword_overlap(artifacts, job_requirements)

        for artifact in ranked:
            self.assertGreaterEqual(artifact['relevance_score'], 0.0)
            self.assertLessEqual(artifact['relevance_score'], 1.0)

    def test_keyword_ranking_case_insensitive(self):
        """Test keyword matching is case-insensitive (ft-007)"""
        service = ArtifactRankingService()

        artifacts = [
            {
                'id': 1,
                'technologies': ['python', 'DJANGO', 'PostgreSQL'],
                'enriched_technologies': []
            }
        ]

        job_requirements = ['Python', 'Django', 'postgresql']

        ranked = service._rank_by_keyword_overlap(artifacts, job_requirements)

        self.assertEqual(len(ranked), 1)
        # Should match all 3 despite case differences
        self.assertEqual(ranked[0]['exact_matches'], 3)
        self.assertGreaterEqual(ranked[0]['relevance_score'], 0.9)


# TestArtifactRankingIntegration class removed (ft-007)
# All embedding/pgvector-related integration tests deprecated
