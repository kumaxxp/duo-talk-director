"""Inject hints from GM into LLM prompt.

Phase 2: Conservative hint injection.
- Only inject on action failure
- Simple, actionable hint
- Positive language
"""

from typing import Optional


class HintInjector:
    """Inject GM hints into prompt.

    Design principles:
    - Only hint on failure (success = no injection)
    - Single specific suggestion
    - Simple markdown format
    """

    @staticmethod
    def inject_hint(prompt: str, gm_response: dict) -> str:
        """Add hint to prompt if action failed.

        Args:
            prompt: Base prompt text
            gm_response: Response from GM service

        Returns:
            Prompt with hint section added (if applicable)
        """
        # Only inject on failure
        if gm_response.get("success", True):
            return prompt

        hint = gm_response.get("hint")
        if not hint:
            return prompt

        hint_section = "\n\n## ヒント\n\n"
        hint_section += hint.get("message", "") + "\n"

        suggested = hint.get("suggested_action")
        if suggested:
            action = suggested.get("action", "")
            args = suggested.get("args", [])
            desc = suggested.get("description", "")

            if args:
                args_str = " ".join(args)
                hint_section += f"\n**推奨**: `{action} {args_str}` - {desc}\n"
            else:
                hint_section += f"\n**推奨**: `{action}` - {desc}\n"

        return prompt + hint_section

    @staticmethod
    def format_hint_for_display(hint: Optional[dict]) -> str:
        """Format hint for console/UI display.

        Args:
            hint: Hint dictionary from GM response

        Returns:
            Formatted string for display
        """
        if not hint:
            return ""

        lines = [hint.get("message", "")]

        suggested = hint.get("suggested_action")
        if suggested:
            action = suggested.get("action", "")
            args = suggested.get("args", [])
            desc = suggested.get("description", "")

            if args:
                args_str = " ".join(args)
                lines.append(f"  -> 推奨: {action} {args_str} ({desc})")
            else:
                lines.append(f"  -> 推奨: {action} ({desc})")

        return "\n".join(lines)
