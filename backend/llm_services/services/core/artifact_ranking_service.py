"""
ArtifactRankingService - Rank artifacts by keyword relevance to job requirements.

This service handles:
- Keyword-based ranking with fuzzy matching
- Artifact ranking based on job requirements
- Recency weighting for recent artifacts
- Relevance scoring with matched keywords

Implements ft-007: Manual Artifact Selection with Keyword Ranking
"""

import logging
from typing import List, Dict, Any
from datetime import date, timedelta
from ..base.base_service import BaseLLMService

logger = logging.getLogger(__name__)


class ArtifactRankingService(BaseLLMService):
    """
    Service for ranking artifacts by keyword relevance to job requirements.
    Uses keyword/technology overlap with fuzzy matching and recency weighting.
    """

    def __init__(self):
        super().__init__()

    def _get_service_config(self) -> Dict[str, Any]:
        """Get artifact ranking specific configuration"""
        return self.settings_manager.get_llm_config()

    async def rank_artifacts_by_relevance(self,
                                         artifacts: List[Dict[str, Any]],
                                         job_requirements: List[str],
                                         strategy: str = 'keyword') -> List[Dict[str, Any]]:
        """
        Rank artifacts by relevance to job requirements.

        Args:
            artifacts: List of artifact dictionaries
            job_requirements: List of required skills/technologies
            strategy: Ranking strategy - only 'keyword' is supported (ft-007)

        Returns:
            Ranked list of artifacts with relevance scores and matched keywords
        """
        if not artifacts:
            return []

        logger.info(f"Ranking {len(artifacts)} artifacts against {len(job_requirements)} requirements using {strategy} strategy")

        # Only keyword ranking is supported (ft-007)
        ranked = self._rank_by_keyword_overlap(artifacts, job_requirements)

        return ranked

    def _rank_by_keyword_overlap(self,
                                 artifacts: List[Dict[str, Any]],
                                 job_requirements: List[str]) -> List[Dict[str, Any]]:
        """
        Rank artifacts by keyword/technology overlap with fuzzy matching and recency weighting.

        Features (ft-007):
        - Exact keyword matching (case-insensitive)
        - Fuzzy matching for partial overlaps (e.g., "Node" matches "Node.js")
        - Recency weighting (recent artifacts get a small boost)
        - Returns matched_keywords list for UI display

        Args:
            artifacts: List of artifact dictionaries
            job_requirements: List of required skills/technologies

        Returns:
            Ranked list with relevance_score (0.0-1.0), exact_matches, partial_matches,
            fuzzy_matches, matched_keywords
        """
        artifacts_with_scores = []

        job_requirements_lower = set(req.lower() for req in job_requirements)

        for artifact in artifacts:
            # Extract technologies from artifact
            artifact_techs = artifact.get('technologies', [])
            enriched_techs = artifact.get('enriched_technologies', [])
            all_techs = set(tech.lower() for tech in (artifact_techs + enriched_techs))

            # Track matched keywords for UI display
            matched_keywords = []

            # Calculate exact match overlap
            exact_matches = 0
            for req in job_requirements:
                req_lower = req.lower()
                if req_lower in all_techs:
                    exact_matches += 1
                    matched_keywords.append(req)  # Use original case from job_requirements

            # Calculate partial match overlap (fuzzy matching)
            # Only count as partial if NOT an exact match
            partial_matches = 0
            exact_match_reqs = all_techs & job_requirements_lower
            for req in job_requirements_lower:
                if req in exact_match_reqs:
                    continue  # Skip if already an exact match
                for tech in all_techs:
                    if req != tech and (req in tech or tech in req):
                        partial_matches += 1
                        break

            # Calculate fuzzy matches (same as partial_matches for now)
            fuzzy_matches = partial_matches

            # Calculate base relevance score (0.0 to 1.0)
            total_requirements = len(job_requirements_lower)
            if total_requirements > 0:
                base_score = (
                    (exact_matches * 1.0 + partial_matches * 0.5) / total_requirements
                )
            else:
                base_score = 0.0

            # Apply recency weighting (ft-007)
            recency_boost = self._calculate_recency_boost(artifact)
            relevance_score = min(1.0, base_score + recency_boost)

            artifacts_with_scores.append({
                **artifact,
                'relevance_score': relevance_score,
                'recency_boost': recency_boost,  # Store for secondary sort
                'ranking_method': 'keyword',
                'exact_matches': exact_matches,
                'partial_matches': partial_matches,
                'fuzzy_matches': fuzzy_matches,
                'matched_keywords': matched_keywords
            })

        # Sort by relevance score (primary), then recency_boost (secondary) for ties
        artifacts_with_scores.sort(key=lambda x: (x['relevance_score'], x['recency_boost']), reverse=True)

        return artifacts_with_scores

    def _calculate_recency_boost(self, artifact: Dict[str, Any]) -> float:
        """
        Calculate recency boost for artifact based on end_date.

        Recent artifacts (within last year) get a small boost (0.0-0.1).
        This helps surface recent work experience when scores are similar.

        Args:
            artifact: Artifact dictionary with optional 'end_date' field

        Returns:
            Recency boost value (0.0 to 0.1)
        """
        try:
            end_date_str = artifact.get('end_date')
            if not end_date_str:
                return 0.0

            # Parse date (ISO format: YYYY-MM-DD)
            if isinstance(end_date_str, str):
                end_date = date.fromisoformat(end_date_str)
            elif isinstance(end_date_str, date):
                end_date = end_date_str
            else:
                return 0.0

            # Calculate days since end date
            today = date.today()
            days_ago = (today - end_date).days

            # Recent artifacts (within 1 year) get boost
            # Linear decay: 0-365 days -> 0.1-0.0 boost
            if days_ago < 0:
                # Future date (currently ongoing) - max boost
                return 0.1
            elif days_ago <= 365:
                # Linear decay over 1 year
                return 0.1 * (1 - days_ago / 365)
            else:
                # Older than 1 year - no boost
                return 0.0

        except Exception as e:
            logger.debug(f"Could not calculate recency boost: {e}")
            return 0.0

    def _build_task_function(self, task_type: str):
        """Build task-specific functions for unified task executor"""
        # Not needed for ranking service (no LLM calls)
        pass
