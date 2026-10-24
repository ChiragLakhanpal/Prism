"""Supplier names as name matching compares them, and a one-row joint venture's members.

normalize() folds a name so that the same firm written two ways reads the same:

- transliteration: accents are taken off (Société is SOCIETE) and letters with no plain form are
  spelled out (ß is SS, Ø is O). A name with no Latin letter or digit left has no normalized form, so
  it is never matched;
- punctuation: every mark is a space, "&" is AND, a run of single letters is one word (S.A. is SA,
  H. P. is HP), and "M/S" or "The" at the front goes;
- legal forms: LTD, LIMITED, PVT, GMBH, S.A. and the other forms in LEGAL_FORMS go from the end of
  the name, so ROAD AND BRIDGE WORKS (K) PVT. LTD. is ROAD AND BRIDGE WORKS K.

joint_venture_members() reads the members of a name the FY2001 to FY2016 awards write as one row,
such as "ECORYS NEDERLAND B.V. IN JV WITH ECORYS INDIA PVT. LTD.".
"""

from __future__ import annotations

import re
import unicodedata

# Legal forms that end a firm's name, in capitals with their punctuation taken off.
LEGAL_FORMS = frozenset({
    "AB", "AG", "AS", "BHD", "BV", "CJSC", "CO", "COMPANY", "CORP", "CORPORATION", "CV", "EIRL", "GMBH", "INC",
    "INCORPORATED", "JSC", "KG", "KK", "LIMITED", "LLC", "LLP", "LTD", "LTDA", "NV", "OJSC", "OOO", "OY", "PLC",
    "PRIVATE", "PTE", "PTY", "PVT", "SA", "SAC", "SARL", "SAS", "SDN", "SL", "SPA", "SRL",
})
SPELLED_OUT = str.maketrans({"ß": "SS", "Ø": "O", "ø": "O", "Æ": "AE", "æ": "AE", "Œ": "OE", "œ": "OE", "Ł": "L",
                             "ł": "L", "Đ": "D", "đ": "D", "Þ": "TH", "þ": "TH", "ı": "I"})
FRONT = re.compile(r"^\s*(M/S\.?|MESSRS\.?)\s*")
JOINT_VENTURE = re.compile(r"\s*,?\s*\b(?:IN\s+(?:A\s+)?)?(?:JV|J\.V\.|JOINT\s+VENTURE)\s+WITH\b\s*", re.I)


def _words(name: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", name.translate(SPELLED_OUT))
    folded = "".join(character for character in folded if not unicodedata.combining(character)).upper()
    folded = FRONT.sub("", folded).replace("&", " AND ")
    words, letters = [], ""
    for word in re.sub(r"[^A-Z0-9]+", " ", folded).split():
        if len(word) == 1 and word.isalpha():
            letters += word
            continue
        if letters:
            words.append(letters)
            letters = ""
        words.append(word)
    if letters:
        words.append(letters)
    return words[1:] if words[:1] == ["THE"] and len(words) > 1 else words


def normalize(name: str | None) -> str | None:
    """The name as name matching compares it, or None when nothing is left to compare."""
    words = _words(name or "")
    kept = list(words)
    while kept and (kept[-1] in LEGAL_FORMS or kept[-1] == "AND"):
        kept.pop()
    return " ".join(kept or words) or None


def joint_venture_members(name: str) -> list[str]:
    """The members a one-row joint venture's name lists, or the name alone when it lists none."""
    members = [part.strip(" ,") for part in JOINT_VENTURE.split(name)]
    return [member for member in members if member] or [name]
