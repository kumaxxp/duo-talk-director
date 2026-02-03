"""Inject state diff into LLM prompt.

Phase 3: State change notification.
- Show inventory changes
- Show location changes
- Show unlocked/opened props
"""

from typing import Optional


class StateDiffInjector:
    """Inject state changes into prompt.

    Design principles:
    - Only inject on success (failures handled by HintInjector)
    - Clear, simple notifications
    - Use positive language
    """

    @staticmethod
    def inject_state_diff(prompt: str, gm_response: dict) -> str:
        """Add state diff notification to prompt.

        Args:
            prompt: Base prompt text
            gm_response: Response from GM service

        Returns:
            Prompt with state diff section added (if applicable)
        """
        if not gm_response.get("success", False):
            return prompt  # Only inject on success

        state_diff = gm_response.get("state_diff")
        if not state_diff:
            return prompt  # No changes

        diff_section = "\n\n## 状態変化\n\n"

        # Inventory added
        if state_diff.get("inventory_added"):
            for item in state_diff["inventory_added"]:
                diff_section += f"**{item}** を入手しました\n"

        # Inventory removed
        if state_diff.get("inventory_removed"):
            for item in state_diff["inventory_removed"]:
                diff_section += f"**{item}** を手放しました\n"

        # Location changed
        if state_diff.get("location_changed"):
            change = state_diff["location_changed"]
            to_loc = change.get("to", "")
            diff_section += f"**{to_loc}** に移動しました\n"

        # Props unlocked
        if state_diff.get("props_unlocked"):
            for prop in state_diff["props_unlocked"]:
                diff_section += f"**{prop}** を解錠しました\n"

        # Props opened
        if state_diff.get("props_opened"):
            for prop in state_diff["props_opened"]:
                diff_section += f"**{prop}** を開けました\n"

        return prompt + diff_section

    @staticmethod
    def format_state_diff_for_display(state_diff: Optional[dict]) -> str:
        """Format state diff for console/UI display.

        Args:
            state_diff: State diff dictionary from GM response

        Returns:
            Formatted string for display
        """
        if not state_diff:
            return ""

        lines = []

        # Inventory added
        if state_diff.get("inventory_added"):
            for item in state_diff["inventory_added"]:
                lines.append(f"  + {item} を入手")

        # Inventory removed
        if state_diff.get("inventory_removed"):
            for item in state_diff["inventory_removed"]:
                lines.append(f"  - {item} を手放し")

        # Location changed
        if state_diff.get("location_changed"):
            change = state_diff["location_changed"]
            lines.append(f"  -> {change.get('to', '')} に移動")

        # Props unlocked
        if state_diff.get("props_unlocked"):
            for prop in state_diff["props_unlocked"]:
                lines.append(f"  [unlock] {prop}")

        # Props opened
        if state_diff.get("props_opened"):
            for prop in state_diff["props_opened"]:
                lines.append(f"  [open] {prop}")

        return "\n".join(lines)
