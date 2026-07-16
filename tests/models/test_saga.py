from mtg_engine.models.saga import (
    parse_chapters_from_oracle, get_final_chapter, get_chapter_text,
    SagaModel,
)
from mtg_engine.models.card_type import (
    EnchantmentSubtype, parse_type_line,
)


class TestCardTypeSagaMethods:
    def test_is_saga_true(self):
        ct = parse_type_line("Enchantment — Saga")
        assert ct.is_saga()
        assert ct.is_enchantment()
        assert EnchantmentSubtype.SAGA.value in ct.subtypes

    def test_is_saga_false(self):
        ct = parse_type_line("Enchantment — Aura")
        assert not ct.is_saga()
        assert ct.is_aura()


class TestParseChapters:
    def test_single_chapter(self):
        chapters = parse_chapters_from_oracle(
            "I — Scry 1. Draw a card."
        )
        assert chapters == [1]

    def test_multiple_chapters(self):
        chapters = parse_chapters_from_oracle(
            "I — Scry 1.\nII — Draw a card.\nIII — You win the game."
        )
        assert chapters == [1, 2, 3]

    def test_two_chapters(self):
        chapters = parse_chapters_from_oracle(
            "I — Create a token.\nII — Sacrifice a creature."
        )
        assert chapters == [1, 2]

    def test_empty_oracle(self):
        chapters = parse_chapters_from_oracle("")
        assert chapters == []

    def test_no_chapters(self):
        chapters = parse_chapters_from_oracle(
            "Enchanted creature gets +1/+1."
        )
        assert chapters == []

    def test_roman_numeral_without_chapter_format(self):
        chapters = parse_chapters_from_oracle(
            "This costs {1} less to cast for each creature you control."
        )
        assert chapters == []

    def test_chapters_with_combined_notation(self):
        chapters = parse_chapters_from_oracle(
            "I, II — Draw a card.\nIII — You win the game."
        )
        assert chapters == [1, 2, 3]

    def test_chapters_up_to_five(self):
        chapters = parse_chapters_from_oracle(
            "I — Do thing.\nII — Do thing.\nIII — Do thing.\n"
            "IV — Do thing.\nV — Do thing."
        )
        assert chapters == [1, 2, 3, 4, 5]


class TestGetFinalChapter:
    def test_three_chapters(self):
        assert get_final_chapter(
            "I — First.\nII — Second.\nIII — Third."
        ) == 3

    def test_two_chapters(self):
        assert get_final_chapter(
            "I — First.\nII — Second."
        ) == 2

    def test_one_chapter(self):
        assert get_final_chapter(
            "I — Only chapter."
        ) == 1

    def test_no_chapters_fallback(self):
        assert get_final_chapter("Just some text.") == 3

    def test_empty_fallback(self):
        assert get_final_chapter("") == 3


class TestGetChapterText:
    def test_get_chapter_one(self):
        text = get_chapter_text(
            "I — Scry 1.\nII — Draw a card.\nIII — You win the game.",
            1,
        )
        assert text == "Scry 1."

    def test_get_chapter_two(self):
        text = get_chapter_text(
            "I — Scry 1.\nII — Draw a card.\nIII — You win the game.",
            2,
        )
        assert text == "Draw a card."

    def test_get_chapter_three(self):
        text = get_chapter_text(
            "I — Scry 1.\nII — Draw a card.\nIII — You win the game.",
            3,
        )
        assert text == "You win the game."

    def test_chapter_not_found(self):
        text = get_chapter_text(
            "I — Scry 1.\nII — Draw a card.",
            5,
        )
        assert text is None

    def test_empty_oracle(self):
        text = get_chapter_text("", 1)
        assert text is None


class TestSagaModel:
    def test_create_saga(self):
        saga = SagaModel(
            name="The Birth of Meletis",
            oracle_text="I — Scry 1.\nII — Draw a card.\nIII — You win the game.",
        )
        assert saga.name == "The Birth of Meletis"
        assert saga.lore_counters == 0
        assert not saga.is_final_chapter_active

    def test_from_oracle_text_three_chapters(self):
        saga = SagaModel.from_oracle_text(
            "The Birth of Meletis",
            "I — Scry 1.\nII — Draw a card.\nIII — You win the game.",
            "Enchantment — Saga",
        )
        assert saga.chapters == [1, 2, 3]
        assert saga.final_chapter == 3

    def test_advance_lore_counter(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.\nIII — Third.",
            chapters=[1, 2, 3],
            final_chapter=3,
        )
        chapter = saga.advance()
        assert chapter == 1
        assert saga.lore_counters == 1
        assert not saga.is_final_chapter_active

    def test_advance_to_final_chapter(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            chapters=[1, 2],
            final_chapter=2,
            lore_counters=1,
        )
        assert not saga.is_final_chapter_active
        chapter = saga.advance()
        assert chapter == 2
        assert saga.lore_counters == 2
        assert saga.is_final_chapter_active
        assert saga.final_chapter_triggered

    def test_should_sacrifice_after_final(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            chapters=[1, 2],
            final_chapter=2,
            lore_counters=2,
        )
        assert saga.should_sacrifice()

    def test_should_not_sacrifice_before_final(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            chapters=[1, 2],
            final_chapter=2,
            lore_counters=1,
        )
        assert not saga.should_sacrifice()

    def test_mark_chapter_resolved(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            chapters=[1, 2],
            final_chapter=2,
        )
        saga.mark_chapter_resolved(1)
        assert 1 in saga.chapter_abilities_resolved
        saga.mark_chapter_resolved(1)
        assert len(saga.chapter_abilities_resolved) == 1

    def test_get_chapter_text(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — Scry 1.\nII — Draw a card.\nIII — Win.",
        )
        assert saga.get_chapter_text(2) == "Draw a card."

    def test_reset(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            chapters=[1, 2],
            final_chapter=2,
            lore_counters=2,
            final_chapter_triggered=True,
            chapter_abilities_resolved=[1, 2],
        )
        saga.reset()
        assert saga.lore_counters == 0
        assert not saga.final_chapter_triggered
        assert saga.chapter_abilities_resolved == []

    def test_current_chapter_property(self):
        saga = SagaModel(
            name="Test Saga",
            oracle_text="I — First.\nII — Second.",
            lore_counters=1,
        )
        assert saga.current_chapter == 1
