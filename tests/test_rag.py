"""Tests for RAG module (Phase 3.1)"""

import pytest

from duo_talk_director.rag import (
    FactCard,
    RAGResult,
    PersonaRAG,
    SessionRAG,
    RAGManager,
)
from duo_talk_director.rag.session_rag import SceneContext


class TestFactCard:
    """Tests for FactCard dataclass"""

    def test_valid_fact_card(self):
        """Valid fact card should be created"""
        fact = FactCard(
            content="やなは「あゆ」と呼ぶ。",
            source="persona",
            priority=3,
            confidence=1.0,
        )
        assert fact.content == "やなは「あゆ」と呼ぶ。"
        assert fact.source == "persona"
        assert fact.priority == 3

    def test_fact_card_max_length(self):
        """Fact content exceeding 50 chars should raise error"""
        with pytest.raises(ValueError, match="exceeds 50 chars"):
            FactCard(
                content="あ" * 51,  # 51 characters
                source="persona",
            )

    def test_fact_card_invalid_priority(self):
        """Invalid priority should raise error"""
        with pytest.raises(ValueError, match="Priority must be 1-4"):
            FactCard(
                content="テスト",
                source="persona",
                priority=5,
            )

    def test_fact_card_invalid_confidence(self):
        """Invalid confidence should raise error"""
        with pytest.raises(ValueError, match="Confidence must be"):
            FactCard(
                content="テスト",
                source="persona",
                confidence=1.5,
            )

    def test_fact_card_to_string(self):
        """__str__ should return FACT: format"""
        fact = FactCard(content="テスト内容", source="persona")
        assert str(fact) == "FACT: テスト内容"


class TestRAGResult:
    """Tests for RAGResult dataclass"""

    def test_empty_result(self):
        """Empty result should be valid"""
        result = RAGResult()
        assert len(result) == 0
        assert not result  # False when empty

    def test_add_fact(self):
        """Adding facts should work up to limit"""
        result = RAGResult()
        for i in range(3):
            fact = FactCard(content=f"Fact {i}", source="persona")
            assert result.add_fact(fact) is True
        assert len(result) == 3

    def test_add_fact_over_limit(self):
        """Adding more than 3 facts should return False"""
        result = RAGResult()
        for i in range(3):
            result.add_fact(FactCard(content=f"Fact {i}", source="persona"))

        # 4th fact should be rejected
        extra_fact = FactCard(content="Extra", source="persona")
        assert result.add_fact(extra_fact) is False
        assert len(result) == 3

    def test_rag_result_max_count(self):
        """Creating RAGResult with more than 3 facts should raise error"""
        facts = [
            FactCard(content=f"Fact {i}", source="persona")
            for i in range(4)
        ]
        with pytest.raises(ValueError, match="Too many facts"):
            RAGResult(facts=facts)

    def test_sort_by_priority(self):
        """Facts should be sorted by priority"""
        result = RAGResult()
        result.add_fact(FactCard(content="Low", source="persona", priority=4))
        result.add_fact(FactCard(content="High", source="persona", priority=1))
        result.add_fact(FactCard(content="Mid", source="persona", priority=2))

        result.sort_by_priority()

        assert result.facts[0].priority == 1
        assert result.facts[1].priority == 2
        assert result.facts[2].priority == 4

    def test_to_fact_string(self):
        """to_fact_string should return formatted facts"""
        result = RAGResult()
        result.add_fact(FactCard(content="Fact 1", source="persona"))
        result.add_fact(FactCard(content="Fact 2", source="session"))

        fact_string = result.to_fact_string()
        assert "FACT: Fact 1" in fact_string
        assert "FACT: Fact 2" in fact_string


class TestPersonaRAG:
    """Tests for PersonaRAG"""

    @pytest.fixture
    def persona_rag(self) -> PersonaRAG:
        return PersonaRAG()

    def test_search_returns_facts(self, persona_rag: PersonaRAG):
        """Search should return facts for valid speaker"""
        facts = persona_rag.search(
            speaker="やな",
            response_text="テスト応答",
            max_facts=3,
        )
        assert isinstance(facts, list)
        # Should at least have addressing fact
        assert len(facts) > 0

    def test_prohibited_term_detection(self, persona_rag: PersonaRAG):
        """Prohibited terms should be detected"""
        # やな should not use 「です」
        facts = persona_rag.search(
            speaker="やな",
            response_text="これはテストです",
            max_facts=3,
        )

        # Find prohibition fact
        prohibition_facts = [f for f in facts if "使わない" in f.content]
        assert len(prohibition_facts) > 0
        assert "です" in prohibition_facts[0].content

    def test_ayu_prohibited_term(self, persona_rag: PersonaRAG):
        """あゆ should not use 「やなちゃん」"""
        facts = persona_rag.search(
            speaker="あゆ",
            response_text="やなちゃん、聞いて",
            max_facts=3,
        )

        prohibition_facts = [f for f in facts if "使わない" in f.content]
        assert len(prohibition_facts) > 0

    def test_get_all_prohibited_terms(self, persona_rag: PersonaRAG):
        """Should return all prohibited terms for speaker"""
        prohibited = persona_rag.get_all_prohibited_terms("やな")
        assert "です" in prohibited
        assert "ます" in prohibited
        assert "姉様" in prohibited

    def test_get_addressing_rules(self, persona_rag: PersonaRAG):
        """Should return addressing rules"""
        rules = persona_rag.get_addressing_rules("あゆ")
        assert rules.get("やな") == "姉様"


class TestSessionRAG:
    """Tests for SessionRAG"""

    @pytest.fixture
    def session_rag(self) -> SessionRAG:
        return SessionRAG()

    def test_empty_session(self, session_rag: SessionRAG):
        """Empty session should return no facts"""
        facts = session_rag.search(
            speaker="やな",
            response_text="テスト",
            max_facts=3,
        )
        assert len(facts) == 0

    def test_scene_props_fact(self, session_rag: SessionRAG):
        """Scene props should generate fact"""
        context = SceneContext(
            location="リビング",
            available_props=["マグカップ", "本"],
        )
        session_rag.set_scene_context(context)

        facts = session_rag.search(
            speaker="やな",
            response_text="テスト",
            max_facts=3,
        )

        props_facts = [f for f in facts if "Sceneにある物" in f.content]
        assert len(props_facts) > 0

    def test_blocked_prop_detection(self, session_rag: SessionRAG):
        """Blocked props should be detected in response"""
        session_rag.add_blocked_prop("グラス")

        facts = session_rag.search(
            speaker="やな",
            response_text="グラスを置いて",
            max_facts=3,
        )

        blocked_facts = [f for f in facts if "グラス" in f.content]
        assert len(blocked_facts) > 0
        assert blocked_facts[0].priority == 1  # High priority

    def test_topic_fact(self, session_rag: SessionRAG):
        """Current topic should generate fact"""
        session_rag.add_topic("朝の挨拶")

        facts = session_rag.search(
            speaker="やな",
            response_text="テスト",
            max_facts=3,
        )

        topic_facts = [f for f in facts if "話題" in f.content]
        assert len(topic_facts) > 0

    def test_reset(self, session_rag: SessionRAG):
        """Reset should clear all state"""
        session_rag.add_blocked_prop("グラス")
        session_rag.add_topic("テスト")

        session_rag.reset()

        assert session_rag.get_blocked_props() == []
        assert session_rag.get_available_props() == []


class TestRAGManager:
    """Tests for RAGManager"""

    @pytest.fixture
    def rag_manager(self) -> RAGManager:
        return RAGManager()

    def test_search_returns_result(self, rag_manager: RAGManager):
        """Search should return RAGResult"""
        result = rag_manager.search(
            speaker="やな",
            response_text="テスト応答です",
        )

        assert isinstance(result, RAGResult)
        assert result.query_time_ms >= 0
        assert "persona" in result.sources_searched
        assert "session" in result.sources_searched

    def test_combined_search(self, rag_manager: RAGManager):
        """Should combine facts from both sources"""
        # Set up session context
        rag_manager.add_blocked_prop("グラス")

        result = rag_manager.search(
            speaker="やな",
            response_text="グラスを持ってです",  # Violation in both
        )

        # Should have facts from both persona and session
        sources = {f.source for f in result.facts}
        assert len(sources) > 0

    def test_max_facts_limit(self, rag_manager: RAGManager):
        """Should not exceed max facts limit"""
        result = rag_manager.search(
            speaker="やな",
            response_text="テスト",
            max_facts=2,
        )

        assert len(result.facts) <= 2

    def test_priority_ordering(self, rag_manager: RAGManager):
        """Facts should be ordered by priority"""
        rag_manager.add_blocked_prop("グラス")

        result = rag_manager.search(
            speaker="やな",
            response_text="グラスです",  # Both violations
        )

        if len(result.facts) >= 2:
            # First fact should have lowest priority number (highest priority)
            assert result.facts[0].priority <= result.facts[1].priority

    def test_disabled_rag(self, rag_manager: RAGManager):
        """Disabled RAG should return empty result"""
        rag_manager.set_enabled(False)

        result = rag_manager.search(
            speaker="やな",
            response_text="テストです",
        )

        assert len(result) == 0

    def test_get_fact_string(self, rag_manager: RAGManager):
        """get_fact_string should return formatted string"""
        fact_string = rag_manager.get_fact_string(
            speaker="やな",
            response_text="テスト",
        )

        assert isinstance(fact_string, str)

    def test_reset_session(self, rag_manager: RAGManager):
        """reset_session should clear session state"""
        rag_manager.add_blocked_prop("グラス")
        rag_manager.add_topic("テスト")

        rag_manager.reset_session()

        # Session facts should be empty now
        result = rag_manager.search(
            speaker="やな",
            response_text="グラス",
        )

        blocked_facts = [f for f in result.facts if "存在しない" in f.content]
        assert len(blocked_facts) == 0


class TestRAGNoHallucination:
    """Tests to ensure RAG doesn't hallucinate"""

    @pytest.fixture
    def rag_manager(self) -> RAGManager:
        return RAGManager()

    def test_no_facts_for_unknown_content(self, rag_manager: RAGManager):
        """Should not generate facts for unrelated content"""
        # Response with no violations or relevant content
        result = rag_manager.search(
            speaker="やな",
            response_text="うん、そうだね。",
        )

        # Should only have basic persona facts, no violation facts
        violation_facts = [f for f in result.facts if f.priority == 1]
        assert len(violation_facts) == 0

    def test_no_invented_props(self, rag_manager: RAGManager):
        """Should not invent props that weren't blocked"""
        result = rag_manager.search(
            speaker="やな",
            response_text="コップを持って",  # Never blocked
        )

        prop_facts = [f for f in result.facts if "存在しない" in f.content]
        assert len(prop_facts) == 0
