"""Setting consistency check for world building

Validates that responses don't break the world setting,
particularly the fact that Yana and Ayu live together.
"""

from ..interfaces import CheckResult, DirectorStatus


# Words/phrases indicating sisters live separately (forbidden)
SEPARATION_WORDS = [
    # Sister's house references
    "姉様のお家", "姉様の家", "姉様の実家",
    "あゆのお家", "あゆの家", "あゆの実家",
    "やなのお家", "やなの家", "やなの実家",
    "姉の家", "妹の家", "姉の実家", "妹の実家",
    # Visiting phrases
    "また来てね", "また遊びに来て", "お邪魔しました",
    # Childhood home references
    "実家では", "実家に", "実家の", "うちの実家",
]


class SettingChecker:
    """Check for setting consistency (sisters live together)"""

    def __init__(
        self,
        separation_words: list[str] | None = None,
    ):
        self.separation_words = separation_words or SEPARATION_WORDS

    def check(
        self,
        response: str,
    ) -> CheckResult:
        """Check for setting-breaking expressions

        Args:
            response: Response text to check

        Returns:
            CheckResult with pass/fail status
        """
        for word in self.separation_words:
            if word in response:
                return CheckResult(
                    name="setting_check",
                    passed=False,
                    status=DirectorStatus.RETRY,
                    reason=f"設定破壊: 「{word}」は姉妹が別居しているかのような表現です",
                    details={
                        "matched_word": word,
                        "suggestion": "やなとあゆは同じ家に住んでいます。「うちに」「私たちの家」等を使ってください。",
                    },
                )

        return CheckResult(
            name="setting_check",
            passed=True,
            status=DirectorStatus.PASS,
            reason="OK",
        )
