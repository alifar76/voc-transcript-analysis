"""
Injects synthetic automatic-speech-recognition (ASR) style noise into clean
dialogue lines, so transcripts read like real low-quality phone-call output:
no punctuation, filler words, misheard homophones, dropped words, stutters,
and occasional inaudible/crosstalk markers.
"""

import random
import re

FILLERS = ["um", "uh", "like", "you know", "i mean", "so yeah"]

HOMOPHONE_SUBS = {
    "for": "four",
    "to": "two",
    "there": "their",
    "your": "youre",
    "write": "right",
    "know": "no",
    "our": "are",
    "affect": "effect",
    "buy": "by",
}

DROPPABLE_WORDS = {"a", "the", "to", "of", "that", "is", "it"}

ARTIFACT_TOKENS = ["[inaudible]", "[crosstalk]", "[static]", "[dropped call]", "[hold music]"]


def _maybe(prob, rng):
    return rng.random() < prob


def inject_noise(text, severity, rng):
    """severity in [0,1]; higher = noisier (customer/cell lines vs agent headset lines)."""
    words = text.split()
    out = []
    for w in words:
        lw = w.lower()

        # stutter/repeat
        if _maybe(0.05 * severity, rng):
            out.append(lw)

        # homophone substitution
        if lw in HOMOPHONE_SUBS and _maybe(0.35 * severity, rng):
            out.append(HOMOPHONE_SUBS[lw])
            continue

        # drop short filler word
        if lw in DROPPABLE_WORDS and _maybe(0.18 * severity, rng):
            continue

        out.append(lw)

        # insert filler word after this word
        if _maybe(0.06 * severity, rng):
            out.append(rng.choice(FILLERS))

    result = " ".join(out)

    # occasionally inject an artifact token
    if _maybe(0.12 * severity, rng):
        pos = rng.randint(0, len(out)) if out else 0
        out.insert(pos, rng.choice(ARTIFACT_TOKENS))
        result = " ".join(out)

    # occasionally truncate the line to mimic a cutoff/dropped word at the end
    if _maybe(0.08 * severity, rng) and len(out) > 4:
        cut = rng.randint(len(out) - 3, len(out) - 1)
        result = " ".join(out[:cut])

    # strip punctuation most of the time (ASR rarely produces clean punctuation)
    if _maybe(0.85, rng):
        result = re.sub(r"[.,!?;:]", "", result)

    # lowercase most of the time
    if _maybe(0.7, rng):
        result = result.lower()

    return result.strip()
