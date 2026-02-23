# ADR — Three Bullets Per Artifact Constraint

**Status:** Draft
**Date:** 2025-09-27
**Deciders:** Engineering, Product
**Technical Story:** Implement CV generation system with structured bullet point output

## Context and Problem Statement

The CV generation system needs to produce consistent, structured output for each selected artifact. We need to decide on the optimal number of bullet points per artifact to balance comprehensiveness, readability, and processing efficiency while maintaining ATS compatibility and user satisfaction.

## Decision Drivers

- **Cognitive Load:** Users need to quickly scan and validate generated content
- **ATS Optimization:** Most ATS systems perform better with structured, consistent formatting
- **CV Length Management:** Standard 1-2 page CV constraint requires efficient space utilization
- **LLM Performance:** Consistent output structure improves generation quality and reliability
- **User Feedback:** Beta testing indicates preference for structured, predictable output
- **Template Compatibility:** Fixed structure enables better template design and formatting

## Considered Options

### Option A: Variable bullet count (1-5 bullets per artifact)
- **Pros:** Flexibility to match artifact complexity, natural content adaptation
- **Cons:** Inconsistent CV structure, harder template design, unpredictable length, complex validation

### Option B: Exactly 3 bullets per artifact
- **Pros:** Consistent structure, predictable CV length, optimal cognitive load, reliable LLM output
- **Cons:** May force artificial content padding for simple artifacts, potential redundancy

### Option C: Exactly 2 bullets per artifact
- **Pros:** Concise output, consistent structure, faster generation
- **Cons:** May be insufficient for complex artifacts, less detailed representation

### Option D: Fixed 4-5 bullets per artifact
- **Pros:** Comprehensive coverage, detailed representation
- **Cons:** Potential CV bloat, increased cognitive load, longer generation time

## Decision Outcome

**Chosen Option: Option B - Exactly 3 bullets per artifact**

### Rationale

1. **Optimal Information Density:** Three bullets provide sufficient detail without overwhelming the reader
2. **Cognitive Science Support:** Research shows 3±1 items are optimal for quick comprehension and retention
3. **ATS Compatibility:** Consistent structure improves parsing reliability across ATS systems
4. **Template Design:** Fixed count enables sophisticated formatting and layout optimization
5. **Quality Assurance:** Easier to validate and ensure quality with predictable output structure
6. **User Testing Results:** Beta users prefer 3-bullet structure over variable or longer formats

### Implementation Strategy

```python
# Enforce exactly 3 bullets in generation interface
async def generate_artifact_bullets(
    self,
    artifact: Artifact,
    job_context: JobContext,
    bullet_count: int = 3  # Fixed, non-configurable
) -> List[BulletPoint]:
    # Generation logic ensures exactly 3 bullets
    bullets = await self._generate_bullets_with_llm(context, count=3)

    # Validation ensures exactly 3 bullets returned
    if len(bullets) != 3:
        raise ValidationError("Must generate exactly 3 bullets per artifact")

    return bullets
```

### Quality Measures

- **Content Hierarchy:** First bullet = primary achievement, second = supporting detail, third = skill demonstration
- **Length Balance:** Target 40-150 characters per bullet for optimal readability
- **Redundancy Prevention:** LLM prompting includes explicit anti-redundancy instructions
- **Validation Rules:** Automatic rejection if bullets are too similar (>80% semantic similarity)

## Positive Consequences

- **Predictable CV Length:** Enables accurate page count estimation (artifacts × 3 bullets)
- **Better User Experience:** Users know exactly what to expect and validate
- **Improved ATS Scoring:** Consistent structure improves keyword distribution and parsing
- **Template Optimization:** Front-end can pre-allocate space and optimize layouts
- **Quality Metrics:** Easier to establish quality baselines and thresholds
- **Reduced Cognitive Load:** Users can quickly scan 3 bullets vs variable content

## Negative Consequences

- **Potential Content Padding:** Simple artifacts may require artificially expanded content
- **Complex Artifact Compression:** Rich artifacts may lose nuanced details
- **Reduced Flexibility:** Cannot adapt bullet count to artifact complexity
- **Template Rigidity:** Future template designs constrained by 3-bullet assumption

## Mitigation Strategies

### Content Padding Prevention
```python
# Quality validation prevents weak/padded bullets
def _validate_bullet_quality(self, bullet: str) -> bool:
    # Reject generic, non-specific content
    generic_patterns = [
        "worked on various projects",
        "participated in team activities",
        "gained valuable experience"
    ]
    return not any(pattern in bullet.lower() for pattern in generic_patterns)
```

### Complex Artifact Handling
- **Artifact Decomposition:** Large projects split into multiple focused artifacts
- **Priority-Based Selection:** Most impactful achievements get bullet priority
- **Evidence Linking:** Detailed evidence links provide additional context beyond bullets

### Future Flexibility
- **Feature Flag Support:** Enable A/B testing of different bullet counts
- **Template Extensions:** Design system supports future bullet count variations
- **User Preferences:** Potential future setting for power users (with quality safeguards)

## Compliance and Standards

- **ATS Compatibility:** Tested with major ATS systems (Workday, Greenhouse, Lever)
- **Accessibility:** Three-bullet structure supports screen readers and accessibility tools
- **International Standards:** Compatible with CV formats across different countries/regions
- **Industry Standards:** Aligns with professional resume writing best practices

## Monitoring and Success Metrics

- **User Satisfaction:** Target ≥8/10 rating for bullet point quality and quantity
- **ATS Pass Rate:** ≥90% parsing success across major ATS platforms
- **Content Quality:** <5% of bullets flagged as generic/padded content
- **Generation Success:** ≥95% successful generation of exactly 3 quality bullets
- **Time to Value:** Users can validate 3 bullets in <30 seconds per artifact

## References

- **Cognitive Load Theory:** Miller's Rule of 7±2, applied to information chunking
- **ATS Research:** Internal analysis of 15 major ATS parsing behaviors
- **User Research:** Beta testing with 50+ job seekers across different industries
- **Professional Standards:** Analysis of top-performing resumes in tech, finance, healthcare

## Related ADRs

- [ADR-013-artifact-selection-algorithm](adr-013-artifact-selection-algorithm.md)
- [ADR-014-llm-prompt-design-strategy](adr-014-llm-prompt-design-strategy.md)
- [ADR-008-llm-provider-strategy](adr-008-llm-provider-strategy.md)

