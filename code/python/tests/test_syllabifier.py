import pytest

from app.services.syllabifier import syllabify


@pytest.mark.parametrize(
    "word,expected",
    [
        ("hola", ["ho", "la"]),
        ("bueno", ["bue", "no"]),
        ("consejo", ["con", "se", "jo"]),
        ("familia", ["fa", "mi", "lia"]),
        ("problema", ["pro", "ble", "ma"]),
        ("también", ["tam", "bién"]),
        ("tengo", ["ten", "go"]),
        ("todos", ["to", "dos"]),
        ("amigos", ["a", "mi", "gos"]),
        ("muestra", ["mues", "tra"]),
        ("perro", ["pe", "rro"]),  # rr digraph never splits
        ("calle", ["ca", "lle"]),  # ll digraph never splits
        ("ancho", ["an", "cho"]),  # ch digraph never splits
        ("día", ["dí", "a"]),  # accented weak forces hiatus
        ("bien", ["bien"]),  # diphthong stays as one syllable
    ],
)
def test_syllabify_matches_spanish_rules(word, expected):
    assert syllabify(word) == expected


def test_syllabify_handles_short_and_empty_input():
    assert syllabify("") == []
    assert syllabify("a") == ["a"]
    assert syllabify("  ") == []


def test_syllabify_is_case_insensitive_and_strips_non_letters():
    assert syllabify("HOLA") == ["ho", "la"]
    assert syllabify(" hola! ") == ["ho", "la"]
