"""
BulletVerificationService - LLM-based fact-checking for generated content (ft-030).

Implements 4-step verification process to detect hallucinations:
1. Claim Extraction: Break bullet into individual claims
2. Evidence Search: Find relevant evidence in source artifacts
3. Classification: Classify each claim as VERIFIED / INFERRED / UNSUPPORTED
4. Aggregation: Combine results into overall verdict

Uses GPT-5 with high reasoning effort for chain-of-thought fact-checking.

Implements ADR-042: Verification Architecture
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from decimal import Decimal

from llm_services.services.base.base_service import BaseLLMService
from llm_services.services.base.config_registry import TaskType

logger = logging.getLogger(__name__)


class BulletVerificationService(BaseLLMService):
    """
    Service for verifying generated content against source evidence.

    Key Features:
    - 4-step verification process (claim extraction → evidence → classification → aggregation)
    - GPT-5 with high reasoning effort for accurate fact-checking
    - Circuit breaker for fault tolerance
    - Parallel verification of up to 3 bullets simultaneously
    - Graceful degradation on failures
    """

    def __init__(self):
        """Initialize verification service with VERIFICATION task type for GPT-5 high reasoning"""
        super().__init__(task_type=TaskType.VERIFICATION)
        logger.info("[ft-030] Initialized BulletVerificationService with GPT-5 high reasoning")

    async def verify_single_bullet(
        self,
        bullet: str,
        source_content: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify a single bullet against source content using 4-step process.

        Args:
            bullet: The generated bullet text to verify
            source_content: Source artifact content (evidence)
            user_id: Optional user ID for tracking

        Returns:
            Dict with verification results:
                - classification: VERIFIED / INFERRED / UNSUPPORTED / UNVERIFIED (on error)
                - confidence: 0.0-1.0 confidence in classification
                - hallucination_risk: LOW / MEDIUM / HIGH
                - claims: List of individual claim results
                - overall_classification: Same as classification
                - overall_confidence: Same as confidence
                - cost: LLM API cost for verification
                - error: Optional error message if verification failed
        """
        try:
            # Step 1: Extract claims from bullet
            logger.debug(f"[ft-030] Step 1: Extracting claims from bullet: {bullet[:100]}...")
            claims = await self._extract_claims(bullet)
            logger.info(f"[ft-030] Extracted {len(claims)} claims from bullet")

            # Step 2-3: Build verification prompt and classify claims
            logger.debug("[ft-030] Step 2-3: Building verification prompt and classifying claims")
            verification_prompt = self._build_verification_prompt(bullet, claims, source_content)

            # Get config for model name
            config = self._build_llm_config()
            model_name = config.get('model', 'gpt-5')

            # Call LLM with circuit breaker protection
            try:
                # Check if circuit breaker allows request
                if not await self.circuit_breaker.can_attempt_request(model_name):
                    logger.warning(f"[ft-030] Circuit breaker open for {model_name}, using degraded response")
                    return self._create_error_response(
                        error="Circuit breaker open",
                        confidence=0.3
                    )

                # Make LLM call
                llm_response = await self._call_llm_for_verification(
                    prompt=verification_prompt,
                    user_id=user_id
                )

                # Record success
                await self.circuit_breaker.record_success(model_name)

            except Exception as e:
                # Record failure
                await self.circuit_breaker.record_failure(model_name)
                logger.error(f"[ft-030] LLM verification error: {e}")
                return self._create_error_response(
                    error=f"Verification failed: {str(e)}",
                    confidence=0.3
                )

            # Step 4: Parse and return aggregated results
            logger.debug("[ft-030] Step 4: Parsing and aggregating results")
            result = self._parse_verification_response(llm_response)

            logger.info(
                f"[ft-030] Verification complete: {result['classification']} "
                f"(confidence: {result['confidence']:.2f}, risk: {result['hallucination_risk']})"
            )

            return result

        except asyncio.TimeoutError:
            logger.error("[ft-030] Verification timeout exceeded")
            return self._create_error_response(
                error="Verification timeout",
                confidence=0.2
            )
        except Exception as e:
            logger.error(f"[ft-030] Verification error: {e}", exc_info=True)
            return self._create_error_response(
                error=str(e),
                confidence=0.1
            )

    async def verify_bullet_set(
        self,
        bullets: List[str],
        source_content: str,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Verify multiple bullets in parallel (up to 3 simultaneously).

        Args:
            bullets: List of bullet texts to verify
            source_content: Source artifact content
            user_id: Optional user ID for tracking

        Returns:
            List of verification results (one per bullet)
        """
        logger.info(f"[ft-030] Verifying {len(bullets)} bullets in parallel")

        # Create verification tasks
        tasks = [
            self.verify_single_bullet(bullet, source_content, user_id)
            for bullet in bullets
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[ft-030] Bullet {i} verification failed: {result}")
                final_results.append(self._create_error_response(str(result), 0.1))
            else:
                final_results.append(result)

        return final_results

    async def _extract_claims(self, bullet: str) -> List[str]:
        """
        Step 1: Extract individual claims from a bullet.

        A claim is a single factual assertion that can be independently verified.

        Args:
            bullet: Bullet text

        Returns:
            List of claim strings
        """
        prompt = f"""Extract individual verifiable claims from this CV bullet point.

Bullet: "{bullet}"

Break down the bullet into separate, independent claims that can be fact-checked individually.
Each claim should be a single factual assertion.

Examples:
- "Led team of 5 engineers" → ["Led team of engineers", "Team size was 5"]
- "Improved performance by 40% using Redis" → ["Improved performance by 40%", "Used Redis"]

Return ONLY a JSON object with a "claims" array of strings:
{{"claims": ["claim 1", "claim 2", ...]}}"""

        try:
            response = await self._call_llm_for_extraction(prompt)
            parsed = json.loads(response['content'])
            claims = parsed.get('claims', [bullet])  # Fallback to original bullet

            logger.debug(f"[ft-030] Extracted {len(claims)} claims: {claims}")
            return claims

        except Exception as e:
            logger.warning(f"[ft-030] Claim extraction failed: {e}, using original bullet")
            return [bullet]  # Fallback: treat entire bullet as one claim

    def _build_verification_prompt(
        self,
        bullet: str,
        claims: List[str],
        source_content: str
    ) -> str:
        """
        Step 2-3: Build verification prompt with chain-of-thought instructions.

        Args:
            bullet: Original bullet text
            claims: Extracted claims
            source_content: Source evidence

        Returns:
            Verification prompt string
        """
        claims_formatted = "\n".join([f"  {i+1}. {claim}" for i, claim in enumerate(claims)])

        prompt = f"""You are a fact-checker verifying CV bullet points against source evidence.

BULLET TO VERIFY:
"{bullet}"

EXTRACTED CLAIMS:
{claims_formatted}

SOURCE EVIDENCE:
{source_content}

TASK: For EACH claim, determine if it is supported by the evidence using chain-of-thought reasoning.

CLASSIFICATION CRITERIA:
- VERIFIED: Claim is directly and explicitly supported by source evidence with strong match
- INFERRED: Claim is reasonably implied by source evidence but not explicitly stated
- UNSUPPORTED: Claim has no support in source evidence (potential hallucination)

For each claim, provide:
1. **Classification**: VERIFIED / INFERRED / UNSUPPORTED
2. **Confidence**: 0.0-1.0 (how certain you are)
3. **Evidence**: Exact quote from source (or null if unsupported)
4. **Reasoning**: Chain-of-thought explanation of your classification

Then provide:
- **overall_classification**: The worst classification among all claims (UNSUPPORTED > INFERRED > VERIFIED)
- **overall_confidence**: Weighted average confidence across all claims
- **hallucination_risk**: LOW (all verified) / MEDIUM (some inferred) / HIGH (any unsupported)

Return ONLY valid JSON with this structure:
{{
  "claims": [
    {{
      "claim": "claim text",
      "classification": "VERIFIED",
      "confidence": 0.95,
      "evidence": "exact quote from source",
      "reasoning": "chain-of-thought explanation"
    }}
  ],
  "overall_classification": "VERIFIED",
  "overall_confidence": 0.93,
  "hallucination_risk": "LOW"
}}

Be strict: If a claim cannot be directly verified, mark it as INFERRED or UNSUPPORTED."""

        return prompt

    async def _call_llm_for_verification(
        self,
        prompt: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call LLM API for verification with GPT-5 high reasoning configuration.

        Args:
            prompt: Verification prompt
            user_id: Optional user ID for tracking

        Returns:
            Dict with 'content' and 'cost' keys
        """
        # Get task-specific config (GPT-5 with high reasoning effort)
        config = self._build_llm_config()

        logger.debug(
            f"[ft-030] Calling LLM for verification: "
            f"model={config['model']}, reasoning_effort={config['reasoning_effort']}"
        )

        # Make API call
        response = await self.client_manager.make_completion_call(
            model=config['model'],
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a precise fact-checker. Verify claims against evidence using chain-of-thought reasoning. Be strict and mark unsupported claims.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            max_completion_tokens=config.get('max_completion_tokens', 1500),
            reasoning_effort=config.get('reasoning_effort')
        )

        # Extract content
        content = ''
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
        elif isinstance(response, dict) and 'choices' in response:
            content = response['choices'][0]['message']['content']

        # Calculate cost
        cost = 0.0
        if hasattr(response, 'usage'):
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
            cost = self.registry.calculate_cost(config['model'], prompt_tokens, completion_tokens)
        elif isinstance(response, dict) and 'usage' in response:
            usage = response['usage']
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            cost = self.registry.calculate_cost(config['model'], prompt_tokens, completion_tokens)

        return {
            'content': content,
            'cost': cost
        }

    async def _call_llm_for_extraction(self, prompt: str) -> Dict[str, Any]:
        """Call LLM for claim extraction (lighter task, can use lower reasoning)"""
        response = await self.client_manager.make_completion_call(
            model='gpt-5-mini',  # Extraction is simpler, use mini model
            messages=[
                {
                    'role': 'system',
                    'content': 'You extract individual claims from text. Return only JSON.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            max_completion_tokens=500
        )

        # Extract content
        content = ''
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
        elif isinstance(response, dict) and 'choices' in response:
            content = response['choices'][0]['message']['content']

        return {'content': content, 'cost': 0.0}

    def _parse_verification_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Parse LLM verification response and aggregate results.

        Args:
            llm_response: Raw LLM response

        Returns:
            Structured verification result
        """
        try:
            content = llm_response.get('content', '{}')
            cost = llm_response.get('cost', 0.0)

            # Parse JSON response
            result = json.loads(content)

            # Ensure all required fields exist
            result.setdefault('claims', [])
            result.setdefault('overall_classification', 'UNVERIFIED')
            result.setdefault('overall_confidence', 0.5)
            result.setdefault('hallucination_risk', 'MEDIUM')

            # Add cost
            result['cost'] = float(cost)

            # Add aliases for compatibility
            result['classification'] = result['overall_classification']
            result['confidence'] = result['overall_confidence']

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[ft-030] Failed to parse verification response: {e}")
            return self._create_error_response(
                error="Failed to parse verification response",
                confidence=0.2
            )

    def _create_error_response(
        self,
        error: str,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Create error response with graceful degradation.

        Args:
            error: Error message
            confidence: Degraded confidence level

        Returns:
            Error response dict
        """
        return {
            'classification': 'UNVERIFIED',
            'confidence': confidence,
            'hallucination_risk': 'HIGH',
            'claims': [],
            'overall_classification': 'UNVERIFIED',
            'overall_confidence': confidence,
            'error': error,
            'cost': 0.0
        }
