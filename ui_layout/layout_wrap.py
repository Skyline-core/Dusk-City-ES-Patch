"""Line-wrap long choice-menu options so the auto-sized menu box stays inside the screen.

The choice menu (DialogueChoise / ChoiseButton) lays itself out from the TMP preferred width, with no
maximum width, so a long single line grows the box past the 4:3 viewport and gets cut. The English
originals were at most ~53 visible characters; Spanish can reach ~78. We therefore insert ONE line break
(at the space nearest to the middle) in options longer than LIMIT visible characters.
"""
from __future__ import annotations

import re

LIMIT = 44            # visible characters per line before we break the option in two
_TAG = re.compile(r"<[^>]*>|\{[^}]*\}")


def visible_len(s: str) -> int:
    return len(_TAG.sub("", s).strip())


def wrap_choice(text: str, limit: int = LIMIT) -> str:
    if "\n" in text or "\\n" in text:
        return text
    t = text.rstrip()
    trail = text[len(t):]
    if visible_len(t) <= limit:
        return text
    # candidate break positions = spaces that are not inside <tags>
    spans = [(m.start(), m.end()) for m in re.finditer(r"<[^>]*>", t)]

    def in_tag(i: int) -> bool:
        return any(a <= i < b for a, b in spans)

    spaces = [i for i, c in enumerate(t) if c == " " and not in_tag(i)]
    if not spaces:
        return text
    mid = len(t) / 2
    best = min(spaces, key=lambda i: abs(i - mid))
    return t[:best] + "\n" + t[best + 1:] + trail
