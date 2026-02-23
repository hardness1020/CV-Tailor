"""
Custom exception classes for CV-Tailor services.

These exceptions are raised by service layers to signal business logic errors,
replacing the anti-pattern of returning {"success": False, "error": "..."} dicts.

Usage:
    # OLD (anti-pattern):
    def enrich_artifact(artifact_id):
        try:
            result = do_enrichment()
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # NEW (proper exception handling):
    def enrich_artifact(artifact_id):
        try:
            result = do_enrichment()
            return result
        except SomeError as e:
            raise EnrichmentError(f"Failed to enrich artifact {artifact_id}") from e
"""


class ServiceError(Exception):
    """Base exception for all service-layer errors."""
    pass


class EnrichmentError(ServiceError):
    """Raised when artifact enrichment fails."""
    pass


class GenerationError(ServiceError):
    """Raised when CV/bullet generation fails."""
    pass


class ValidationError(ServiceError):
    """Raised when data validation fails."""
    pass


class RankingError(ServiceError):
    """Raised when artifact ranking fails."""
    pass


class ExtractionError(ServiceError):
    """Raised when content extraction from evidence fails."""
    pass


class LLMServiceError(ServiceError):
    """Raised when LLM API calls fail."""
    pass


class CircuitBreakerOpenError(LLMServiceError):
    """Raised when circuit breaker is open for a model."""
    pass


class ModelSelectionError(LLMServiceError):
    """Raised when no suitable model can be selected."""
    pass


class ContentProcessingError(ServiceError):
    """Raised when content processing (unification, technology extraction, etc.) fails."""
    pass


class EmbeddingError(ServiceError):
    """Raised when embedding generation fails."""
    pass


class ArtifactNotFoundError(ServiceError):
    """Raised when artifact doesn't exist or user doesn't have access."""
    pass


class EvidenceNotFoundError(ServiceError):
    """Raised when evidence doesn't exist or is inaccessible."""
    pass


class InsufficientDataError(ServiceError):
    """Raised when insufficient data is available for processing."""
    pass


class QualityValidationError(ServiceError):
    """Raised when enrichment quality validation fails."""
    pass
