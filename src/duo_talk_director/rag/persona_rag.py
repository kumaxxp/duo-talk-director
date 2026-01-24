"""PersonaRAG - Character settings and rules retrieval

Retrieves facts about character settings, prohibited terms,
and addressing rules from persona_rules.yaml.
"""

from pathlib import Path
from typing import Optional

import yaml

from .fact_card import FactCard


class PersonaRAG:
    """RAG for character persona and rules

    Searches character settings and rules to generate FactCards
    about prohibited terms, addressing rules, and speech patterns.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize PersonaRAG

        Args:
            config_path: Path to persona_rules.yaml.
                        If None, uses default location.
        """
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent / "config" / "persona_rules.yaml"
            )

        self.config_path = config_path
        self._config: Optional[dict] = None

    @property
    def config(self) -> dict:
        """Lazy-load configuration"""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> dict:
        """Load configuration from YAML"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Persona config not found: {self.config_path}"
            )
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def search(
        self,
        speaker: str,
        response_text: str,
        max_facts: int = 3,
    ) -> list[FactCard]:
        """Search for relevant facts based on speaker and response

        Args:
            speaker: Current speaker ("やな" or "あゆ")
            response_text: Response text to check
            max_facts: Maximum number of facts to return

        Returns:
            List of FactCards (up to max_facts)
        """
        facts: list[FactCard] = []

        # Get character config
        char_config = self.config.get("characters", {}).get(speaker)
        if not char_config:
            return facts

        # Check for prohibited terms in response
        prohibited_facts = self._check_prohibited_terms(
            speaker, response_text, char_config
        )
        facts.extend(prohibited_facts)

        # Add addressing rule fact
        addressing_fact = self._get_addressing_fact(speaker, char_config)
        if addressing_fact:
            facts.append(addressing_fact)

        # Add speech style fact
        style_fact = self._get_speech_style_fact(speaker, char_config)
        if style_fact:
            facts.append(style_fact)

        # Sort by priority and limit
        facts.sort(key=lambda f: f.priority)
        return facts[:max_facts]

    def _check_prohibited_terms(
        self,
        speaker: str,
        response_text: str,
        char_config: dict,
    ) -> list[FactCard]:
        """Check for prohibited terms in response

        Returns FactCards for any prohibited terms found.
        """
        facts = []
        speech_style = char_config.get("speech_style", {})
        prohibited = speech_style.get("prohibited", [])

        for term in prohibited:
            if term in response_text:
                fact_content = f"{speaker}は「{term}」を使わない。"
                if len(fact_content) <= 50:
                    facts.append(
                        FactCard(
                            content=fact_content,
                            source="persona",
                            priority=1,  # Highest priority for violations
                            confidence=1.0,
                        )
                    )

        return facts

    def _get_addressing_fact(
        self,
        speaker: str,
        char_config: dict,
    ) -> Optional[FactCard]:
        """Get addressing rule fact for speaker"""
        addressing = char_config.get("addressing", {})

        # Find the target character
        other_char = "あゆ" if speaker == "やな" else "やな"
        address_term = addressing.get(other_char)

        if address_term:
            # Also find what the other character calls this speaker
            other_config = self.config.get("characters", {}).get(other_char, {})
            other_addressing = other_config.get("addressing", {})
            other_term = other_addressing.get(speaker)

            if other_term:
                fact_content = (
                    f"{speaker}は「{address_term}」、"
                    f"{other_char}は「{other_term}」と呼ぶ。"
                )
            else:
                fact_content = f"{speaker}は{other_char}を「{address_term}」と呼ぶ。"

            if len(fact_content) <= 50:
                return FactCard(
                    content=fact_content,
                    source="persona",
                    priority=3,
                    confidence=1.0,
                )

        return None

    def _get_speech_style_fact(
        self,
        speaker: str,
        char_config: dict,
    ) -> Optional[FactCard]:
        """Get speech style fact for speaker"""
        speech_style = char_config.get("speech_style", {})
        tone = speech_style.get("tone")

        if tone:
            fact_content = f"{speaker}の話し方: {tone}。"
            if len(fact_content) <= 50:
                return FactCard(
                    content=fact_content,
                    source="persona",
                    priority=3,
                    confidence=1.0,
                )

        return None

    def get_all_prohibited_terms(self, speaker: str) -> list[str]:
        """Get all prohibited terms for a speaker

        Useful for pre-checking before generation.
        """
        char_config = self.config.get("characters", {}).get(speaker, {})
        speech_style = char_config.get("speech_style", {})
        return speech_style.get("prohibited", [])

    def get_addressing_rules(self, speaker: str) -> dict:
        """Get addressing rules for a speaker"""
        char_config = self.config.get("characters", {}).get(speaker, {})
        return char_config.get("addressing", {})
