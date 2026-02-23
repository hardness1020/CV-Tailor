"""
Generation services package.

Implements service layer for document generation following the architecture
pattern established in llm_services/ (ADR-20251001-generation-service-layer-extraction).

Service modules:
- bullet_generation_service: Generate exactly 3 bullet points per artifact
- bullet_validation_service: Validate bullet quality and structure
- generation_service: Orchestrate document generation workflow (extracted from tasks.py)
"""

from .bullet_generation_service import BulletGenerationService, GeneratedBulletSet
from .bullet_validation_service import BulletValidationService, ValidationResult
from .generation_service import GenerationService, GenerationResult, BulletPreparationResult

__all__ = [
    'BulletGenerationService',
    'GeneratedBulletSet',
    'BulletValidationService',
    'ValidationResult',
    'GenerationService',
    'GenerationResult',
    'BulletPreparationResult',
]
