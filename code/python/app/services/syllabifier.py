"""Lightweight Spanish syllabifier (no third-party dependency).

Splits a Spanish word into syllables using the standard rules:

* Vowels group into a single nucleus when they form a diphthong (weak+strong,
  strong+weak or weak+weak); a hiatus (two strong vowels, or an accented weak
  vowel í/ú next to another vowel) splits them into separate nuclei.
* Consonants between two nuclei are distributed by onset-maximisation: a single
  consonant joins the following syllable (V-CV); inseparable clusters
  (consonant + l/r) and the digraphs ch/ll/rr never split.

It is intentionally dependency-free so the packaged executable keeps working,
and approximate enough for slicing audio at syllable boundaries. It is not a
full phonological parser, but it matches the project's target vocabulary
(hola→ho-la, bueno→bue-no, consejo→con-se-jo, familia→fa-mi-lia,
también→tam-bién, problema→pro-ble-ma).
"""

from __future__ import annotations

VOWELS = set("aeiouáéíóúüàèìòùAEIOUÁÉÍÓÚÜ".lower())
# Strong vowels include accented strong vowels; these force a hiatus next to
# another strong vowel.
STRONG = set("aeoáéó")
# Accented weak vowels break a would-be diphthong into a hiatus.
ACCENTED_WEAK = set("íú")
# Unaccented weak vowels.
WEAK = set("iuü")

# Consonant + l/r clusters that always stay together as a syllable onset.
INSEPARABLE = {
    "bl", "br", "cl", "cr", "dr", "fl", "fr",
    "gl", "gr", "kl", "kr", "pl", "pr", "tr", "tl",
}
# Spanish digraphs that represent a single consonant and never split.
DIGRAPHS = {"ch", "ll", "rr"}


def _is_hiatus(first: str, second: str) -> bool:
    if first in ACCENTED_WEAK or second in ACCENTED_WEAK:
        return True
    if first in STRONG and second in STRONG:
        return True
    return False


def syllabify(word: str) -> list[str]:
    """Return the list of syllables for ``word`` (best-effort, lowercased)."""
    chars = [c for c in word.lower().strip() if c.isalpha()]
    text = "".join(chars)
    if len(text) < 2:
        return [text] if text else []

    n = len(text)
    is_vowel = [c in VOWELS for c in text]

    # 1) Collect vowel nuclei, splitting hiatus inside a vowel run.
    nuclei: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if not is_vowel[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and is_vowel[j + 1]:
            j += 1
        run = list(range(i, j + 1))
        seg_start = run[0]
        for k in range(len(run) - 1):
            if _is_hiatus(text[run[k]], text[run[k + 1]]):
                nuclei.append((seg_start, run[k]))
                seg_start = run[k + 1]
        nuclei.append((seg_start, run[-1]))
        i = j + 1

    if len(nuclei) <= 1:
        return [text]

    # 2) Place a boundary between each pair of nuclei based on the consonants
    #    sitting between them.
    boundaries: list[int] = []
    for idx in range(len(nuclei) - 1):
        end_v = nuclei[idx][1]
        start_v_next = nuclei[idx + 1][0]
        cons = list(range(end_v + 1, start_v_next))
        if not cons:
            split_at = start_v_next
        elif len(cons) == 1:
            split_at = cons[0]
        else:
            pair = text[cons[-2]] + text[cons[-1]]
            if pair in DIGRAPHS or pair in INSEPARABLE:
                split_at = cons[-2]
            else:
                split_at = cons[-1]
        boundaries.append(split_at)

    # 3) Cut the word at the boundaries.
    syllables: list[str] = []
    prev = 0
    for boundary in boundaries:
        syllables.append(text[prev:boundary])
        prev = boundary
    syllables.append(text[prev:])
    return [s for s in syllables if s]
