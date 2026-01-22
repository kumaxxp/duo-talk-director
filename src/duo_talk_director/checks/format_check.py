"""Format check for response structure

Validates that responses are properly formatted:
- Not too long (excessive lines)
- Single coherent utterance
"""

from ..interfaces import CheckResult, DirectorStatus


class FormatChecker:
    """Check response format and length"""

    def __init__(
        self,
        retry_line_threshold: int = 8,
        warn_line_threshold: int = 6,
    ):
        self.retry_line_threshold = retry_line_threshold
        self.warn_line_threshold = warn_line_threshold

    def check(
        self,
        response: str,
    ) -> CheckResult:
        """Check response format

        Args:
            response: Response text to check

        Returns:
            CheckResult with pass/fail status
        """
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        line_count = len(lines)

        if line_count >= self.retry_line_threshold:
            return CheckResult(
                name="format_check",
                passed=False,
                status=DirectorStatus.RETRY,
                reason=f"発言が複数行に分かれすぎています（{line_count}行）",
                details={
                    "line_count": line_count,
                    "suggestion": "1つの連続した発言として、簡潔に出力してください。",
                },
            )

        if line_count >= self.warn_line_threshold:
            return CheckResult(
                name="format_check",
                passed=True,  # WARN is still passing
                status=DirectorStatus.WARN,
                reason=f"発言が複数行です（{line_count}行）",
                details={
                    "line_count": line_count,
                    "suggestion": "1つの連続した発言として、簡潔に出力してください。",
                },
            )

        return CheckResult(
            name="format_check",
            passed=True,
            status=DirectorStatus.PASS,
            reason="OK",
            details={"line_count": line_count},
        )
