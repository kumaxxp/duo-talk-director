"""LLM-based Evaluator (Phase 2.2)

Evaluates dialogue quality using LLM scoring on 5 axes.
"""

import json
import re
from typing import Protocol, Optional

from ..interfaces import LLMEvaluationScore
from .prompts import build_evaluation_prompt


class EvaluatorLLMClient(Protocol):
    """Protocol for LLM client used by evaluator"""

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text from prompt"""
        ...

    def is_available(self) -> bool:
        """Check if backend is available"""
        ...


class LLMEvaluator:
    """LLM-based dialogue quality evaluator.

    Uses LLM to score responses on 5 quality metrics:
    - character_consistency
    - topic_novelty
    - relationship_quality
    - naturalness
    - concreteness
    """

    def __init__(self, llm_client: EvaluatorLLMClient):
        """Initialize evaluator with LLM client.

        Args:
            llm_client: LLM client implementing EvaluatorLLMClient protocol
        """
        self.llm_client = llm_client

    def evaluate_single_turn(
        self,
        speaker: str,
        response: str,
        topic: str,
        history: list[dict],
    ) -> LLMEvaluationScore:
        """Evaluate a single turn response.

        Args:
            speaker: Character name ("やな" or "あゆ")
            response: Response text to evaluate
            topic: Conversation topic
            history: Previous conversation turns

        Returns:
            LLMEvaluationScore with 5-axis scores
        """
        prompt = build_evaluation_prompt(
            speaker=speaker,
            response=response,
            topic=topic,
            history=history,
        )

        try:
            raw_response = self.llm_client.generate(prompt, max_tokens=500)
            return self._parse_response(raw_response)
        except Exception as e:
            # Fallback to default scores on error
            return LLMEvaluationScore(
                character_consistency=0.5,
                topic_novelty=0.5,
                relationship_quality=0.5,
                naturalness=0.5,
                concreteness=0.5,
                issues=[f"LLM evaluation error: {str(e)}"],
            )

    def _parse_response(self, response_text: str) -> LLMEvaluationScore:
        """Parse LLM response and extract scores.

        Args:
            response_text: Raw LLM output

        Returns:
            LLMEvaluationScore extracted from response
        """
        try:
            # Extract JSON from response (may have surrounding text)
            json_match = re.search(
                r'\{[^{}]*"character_consistency"[^{}]*\}',
                response_text,
                re.DOTALL,
            )

            if not json_match:
                # Try more permissive pattern
                json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)

            if json_match:
                json_text = json_match.group(0)
                data = json.loads(json_text)

                return LLMEvaluationScore(
                    character_consistency=self._clamp(data.get("character_consistency", 0.5)),
                    topic_novelty=self._clamp(data.get("topic_novelty", 0.5)),
                    relationship_quality=self._clamp(data.get("relationship_quality", 0.5)),
                    naturalness=self._clamp(data.get("naturalness", 0.5)),
                    concreteness=self._clamp(data.get("concreteness", 0.5)),
                    overall_score=self._clamp(data.get("overall_score", 0.0)),
                    issues=data.get("issues", []),
                    strengths=data.get("strengths", []),
                )

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            pass

        # Default fallback
        return LLMEvaluationScore(
            character_consistency=0.5,
            topic_novelty=0.5,
            relationship_quality=0.5,
            naturalness=0.5,
            concreteness=0.5,
            issues=[f"JSON parse error: could not extract valid JSON"],
        )

    def _clamp(self, value: float) -> float:
        """Clamp value to 0.0-1.0 range.

        Args:
            value: Value to clamp

        Returns:
            Clamped value
        """
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5
