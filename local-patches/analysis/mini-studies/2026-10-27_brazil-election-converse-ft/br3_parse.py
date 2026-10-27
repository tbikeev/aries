"""Parse Astrolog -a aspect lines into BR-3 planetary cells."""

from __future__ import annotations

import re
from dataclasses import dataclass

from br3_schema import ASPECTS, PLANETS, aspect_index, c2c_pair_index

_ASPECT_RE = re.compile(r"\b(Con|Opp|Squ|Tri|Sex)\b")
_POWER_RE = re.compile(r" - power:\s+([0-9.]+)\s*$")
_ORB_RE = re.compile(r" - orb:\s*([+-]?)(\d+):(\d+)'(\d+)\"")
_LEFT_RE = re.compile(r"^\s*\d+:\s+(\S+)")
_RIGHT_RE = re.compile(
    r"(?:Con|Opp|Squ|Tri|Sex)\s+(?:with\s+)?[\(\[][^)\]]+[\)\]]\s+(\S+)",
    re.I,
)

NODE_ALIASES = frozenset({"NNMean", "NNTrue", "NNode", "Node", "MeanNode", "TrueNode"})


def normalize_planet(token: str) -> str | None:
    t = token.strip()
    if t in PLANETS:
        return t
    if t in NODE_ALIASES:
        return "Node"
    return None


def orb_tokens_to_degrees(sign: str, deg: str, minute: str, second: str) -> float:
    val = int(deg) + int(minute) / 60.0 + int(second) / 3600.0
    if sign == "-":
        val = -val
    return val


@dataclass
class ParsedAspect:
    left: str
    right: str
    aspect: str
    power: float
    orb_signed_deg: float
    orb_deg: float
    directed: bool


def parse_aspect_lines(text: str, *, mode: str) -> list[ParsedAspect]:
    """mode: 'c2c' (unordered converse-converse) or 'c2r' (directed converse->radix)."""
    out: list[ParsedAspect] = []
    for line in text.splitlines():
        if " - power:" not in line:
            continue
        mp = _POWER_RE.search(line)
        ma = _ASPECT_RE.search(line)
        ml = _LEFT_RE.match(line)
        mr = _RIGHT_RE.search(line)
        mo = _ORB_RE.search(line)
        if not (mp and ma and ml and mr and mo):
            continue
        asp = ma.group(1).lower()[:3]
        if asp not in ASPECTS:
            continue
        left = normalize_planet(ml.group(1))
        right = normalize_planet(mr.group(1))
        if not left or not right:
            continue
        if mode == "c2c" and left == right:
            continue
        if mode == "c2c" and " with " in line.lower():
            continue
        if mode == "c2r" and " with " not in line.lower():
            continue
        signed = orb_tokens_to_degrees(mo.group(1) or "+", mo.group(2), mo.group(3), mo.group(4))
        out.append(
            ParsedAspect(
                left=left,
                right=right,
                aspect=asp,
                power=float(mp.group(1)),
                orb_signed_deg=signed,
                orb_deg=abs(signed),
                directed=(mode == "c2r"),
            )
        )
    return out


def merge_duplicate_cells(aspects: list[ParsedAspect], *, mode: str) -> dict[tuple, ParsedAspect]:
    """One activation per cell; keep highest power when duplicates (e.g. NNMean/NNTrue)."""
    cells: dict[tuple, ParsedAspect] = {}
    for a in aspects:
        if mode == "c2c":
            key = (c2c_pair_index(a.left, a.right), aspect_index(a.aspect))
        else:
            key = (PLANETS.index(a.left), PLANETS.index(a.right), aspect_index(a.aspect))
        prev = cells.get(key)
        if prev is None or a.power > prev.power:
            cells[key] = a
    return cells
