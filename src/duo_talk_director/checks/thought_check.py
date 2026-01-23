"""Thought check for response structure validation

Validates that responses have proper Thought content:
- Thought is present (not missing)
- Thought has content (not empty)
- Thought is complete (not truncated)
- Output follows Thought
"""

import re
from dataclasses import dataclass

from ..interfaces import CheckResult, DirectorStatus


@dataclass
class ThoughtValidation:
    """Result of Thought validation"""
    has_thought: bool = False
    has_output: bool = False
    thought_content: str = ""
    is_empty: bool = True
    is_truncated: bool = False


class ThoughtChecker:
    """Check Thought presence and validity in responses"""

    # Pattern to extract Thought content
    # Matches: "Thought: ..." until "Output:" or end of string
    THOUGHT_PATTERN = re.compile(
        r"Thought:\s*(.+?)(?=\nOutput:|$)",
        re.DOTALL | re.IGNORECASE
    )

    # Pattern to detect Output marker
    OUTPUT_PATTERN = re.compile(r"Output:", re.IGNORECASE)

    # Patterns indicating empty/truncated Thought
    EMPTY_PATTERNS = [
        re.compile(r"Thought:\s*\(?\s*\n", re.IGNORECASE),  # "Thought: (\n" or "Thought: \n"
        re.compile(r"Thought:\s*$", re.IGNORECASE),  # "Thought:" at end
        re.compile(r"Thought:\s*\(\s*\n", re.IGNORECASE),  # "Thought: ( \n"
    ]

    # Patterns indicating truncated content (incomplete speaker prefix)
    TRUNCATED_PATTERNS = [
        re.compile(r"Thought:\s*\([A-Za-zやなあゆ]+:\s*\n", re.IGNORECASE),  # "Thought: (Yana:\n"
        re.compile(r"Thought:\s*\([A-Za-zやなあゆ]+:\s*$", re.IGNORECASE),  # "Thought: (Yana:" at end
    ]

    def __init__(self, min_thought_length: int = 3):
        """Initialize ThoughtChecker

        Args:
            min_thought_length: Minimum characters for valid Thought content
        """
        self.min_thought_length = min_thought_length

    def check(self, response: str) -> CheckResult:
        """Check Thought validity in response

        Args:
            response: Full response text to check

        Returns:
            CheckResult with pass/fail status
        """
        validation = self._validate_thought(response)

        # Case 1: Missing Thought entirely
        if not validation.has_thought:
            return CheckResult(
                name="thought_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason="Thoughtが見つかりません。思考（Thought）と発言（Output）の2段階で応答してください。",
                details={
                    "error_type": "missing_thought",
                    "suggestion": "Thought: (内面の思考) の形式で思考を出力してください。",
                },
            )

        # Case 2: Empty Thought
        if validation.is_empty:
            return CheckResult(
                name="thought_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason="Thoughtの内容が空です。キャラクターの内面の思考を記述してください。",
                details={
                    "error_type": "empty_thought",
                    "thought_content": validation.thought_content,
                    "suggestion": "Thought: (内面の思考) の形式で思考を出力してください。",
                },
            )

        # Case 3: Truncated Thought
        if validation.is_truncated:
            return CheckResult(
                name="thought_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason="Thoughtが途中で切れています（incomplete）。完全な思考を出力してください。",
                details={
                    "error_type": "truncated_thought",
                    "thought_content": validation.thought_content,
                    "suggestion": "Thoughtは完全な文で終わるようにしてください。",
                },
            )

        # Case 4: Missing Output
        if not validation.has_output:
            return CheckResult(
                name="thought_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason="Outputが見つかりません。Thoughtの後にOutputを出力してください。",
                details={
                    "error_type": "missing_output",
                    "thought_content": validation.thought_content,
                    "suggestion": "Output: (動作) 「発言」 の形式で発言を出力してください。",
                },
            )

        # Case 5: Short Thought (warn but pass)
        thought_len = len(validation.thought_content.strip())
        if thought_len < self.min_thought_length:
            return CheckResult(
                name="thought_check",
                passed=True,  # WARN is still passing
                status=DirectorStatus.WARN,
                reason=f"Thoughtが短すぎます（{thought_len}文字）",
                details={
                    "thought_content": validation.thought_content,
                    "thought_length": thought_len,
                    "min_length": self.min_thought_length,
                },
            )

        # Case 6: Valid Thought
        return CheckResult(
            name="thought_check",
            passed=True,
            status=DirectorStatus.PASS,
            reason="OK",
            details={
                "thought_content": validation.thought_content[:50] + "..."
                if len(validation.thought_content) > 50
                else validation.thought_content,
                "thought_length": thought_len,
            },
        )

    def _validate_thought(self, response: str) -> ThoughtValidation:
        """Validate Thought structure in response

        Args:
            response: Full response text

        Returns:
            ThoughtValidation with analysis results
        """
        result = ThoughtValidation()

        # Check for empty patterns first (these indicate Thought marker exists but empty)
        for pattern in self.EMPTY_PATTERNS:
            if pattern.search(response):
                result.has_thought = True
                result.is_empty = True
                return result

        # Check for truncated patterns
        for pattern in self.TRUNCATED_PATTERNS:
            if pattern.search(response):
                result.has_thought = True
                result.is_empty = True  # Treat truncated speaker prefix as empty
                return result

        # Check for Thought marker
        if "thought:" not in response.lower():
            # No Thought marker at all
            return result

        result.has_thought = True

        # Extract Thought content
        match = self.THOUGHT_PATTERN.search(response)
        if match:
            thought_content = match.group(1).strip()
            result.thought_content = thought_content

            # Check if content is meaningful (not just punctuation or speaker prefix)
            cleaned_content = self._clean_thought_content(thought_content)
            # Empty = truly no content (only whitespace/punctuation)
            # A single character like "…" is considered empty
            result.is_empty = len(cleaned_content) <= 1 or cleaned_content in ["…", "...", "。", "、"]

            # Check for incomplete content (ends mid-sentence without closing)
            if not result.is_empty:
                result.is_truncated = self._is_truncated(thought_content)
        else:
            # Thought marker found but no content could be extracted
            result.is_empty = True

        # Check for Output marker
        result.has_output = bool(self.OUTPUT_PATTERN.search(response))

        return result

    def _clean_thought_content(self, content: str) -> str:
        """Remove speaker prefix, parentheses, and whitespace from Thought content

        Args:
            content: Raw Thought content

        Returns:
            Cleaned content without speaker prefix or wrapper parentheses
        """
        cleaned = content.strip()

        # Remove speaker prefix like "(Yana:" or "(やな:" or "(姉様"
        cleaned = re.sub(r"^\s*\([A-Za-zやなあゆ姉妹様]+:\s*", "", cleaned)

        # Remove wrapper parentheses if content is wrapped: "(content)" -> "content"
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith("("):
            # Remove leading parenthesis if not closed
            cleaned = cleaned[1:]

        # Remove trailing parenthesis if present (unclosed)
        cleaned = re.sub(r"\)\s*$", "", cleaned)

        # Remove leading/trailing whitespace
        return cleaned.strip()

    def _is_truncated(self, content: str) -> bool:
        """Check if Thought content appears truncated

        Args:
            content: Thought content to check

        Returns:
            True if content appears truncated
        """
        # Check for unclosed parenthesis with speaker prefix but no content
        if re.match(r"^\s*\([A-Za-zやなあゆ]+:\s*[^)]{0,5}$", content):
            return True

        # Check for content that ends abruptly (no closing parenthesis when opened)
        open_parens = content.count("(")
        close_parens = content.count(")")
        if open_parens > close_parens and len(content) < 20:
            return True

        return False
