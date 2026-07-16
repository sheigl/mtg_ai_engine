import re
from typing import Optional
from pydantic import BaseModel, Field

ROMAN_TO_INT: dict[str, int] = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}
_INT_TO_ROMAN: dict[int, str] = {v: k for k, v in ROMAN_TO_INT.items()}

_ROMAN_RE = re.compile(r"\b(I{1,3}|IV|V|I?X)\b(?=\s*[,—])")


def parse_chapters_from_oracle(oracle_text: str) -> list[int]:
    """Extract chapter numbers from Saga oracle text.

    Returns a sorted list of chapter numbers found.
    Example: 'I — Scry 1. II — Draw a card.' -> [1, 2]
    """
    if not oracle_text:
        return []
    chapters: set[int] = set()
    for m in _ROMAN_RE.finditer(oracle_text):
        roman = m.group(1)
        val = ROMAN_TO_INT.get(roman)
        if val:
            chapters.add(val)
    return sorted(chapters)


def get_final_chapter(oracle_text: str) -> int:
    """Get the highest chapter number in a Saga's oracle text."""
    chapters = parse_chapters_from_oracle(oracle_text)
    return max(chapters) if chapters else 3


def get_chapter_text(oracle_text: str, chapter: int) -> Optional[str]:
    """Extract the ability text for a specific chapter number."""
    if not oracle_text:
        return None
    roman = _INT_TO_ROMAN.get(chapter)
    if not roman:
        return None
    # Match: "Roman numeral" optionally followed by more roman numerals then " — " then text
    pattern = re.compile(
        rf"\b{roman}\b(?:\s*,\s*[IVX]+)*\s*[—–-]\s*(.*?)(?=\n\s*\b[IVX]+\b\s*[—–-]|\Z)",
        re.DOTALL,
    )
    m = pattern.search(oracle_text)
    if m:
        return m.group(1).strip()
    return None


class SagaModel(BaseModel):
    name: str = ""
    oracle_text: str = ""
    type_line: str = ""
    lore_counters: int = 0
    chapters: list[int] = Field(default_factory=list)
    final_chapter: int = 3
    final_chapter_triggered: bool = False
    chapter_abilities_resolved: list[int] = Field(default_factory=list)

    @staticmethod
    def from_oracle_text(name: str, oracle_text: str, type_line: str) -> "SagaModel":
        chapters = parse_chapters_from_oracle(oracle_text)
        final_chapter = max(chapters) if chapters else 3
        return SagaModel(
            name=name,
            oracle_text=oracle_text,
            type_line=type_line,
            chapters=chapters,
            final_chapter=final_chapter,
        )

    @property
    def current_chapter(self) -> int:
        return self.lore_counters

    @property
    def is_final_chapter_active(self) -> bool:
        return self.lore_counters >= self.final_chapter

    def advance(self) -> Optional[int]:
        self.lore_counters += 1
        new_chapter = self.lore_counters
        if self.lore_counters >= self.final_chapter:
            self.final_chapter_triggered = True
        return new_chapter

    def mark_chapter_resolved(self, chapter: int) -> None:
        if chapter not in self.chapter_abilities_resolved:
            self.chapter_abilities_resolved.append(chapter)

    def get_chapter_text(self, chapter: int) -> Optional[str]:
        return get_chapter_text(self.oracle_text, chapter)

    def should_sacrifice(self) -> bool:
        return self.lore_counters >= self.final_chapter and not self.final_chapter_triggered

    def reset(self) -> None:
        self.lore_counters = 0
        self.final_chapter_triggered = False
        self.chapter_abilities_resolved = []
