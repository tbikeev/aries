"""Resolve ast77 binary + scripts (sa_app vendor or listok)."""

from __future__ import annotations

import os
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent
PROJECTS = STUDY_ROOT.parents[4]  # .../Projects

SA_APP_AST77 = (
    PROJECTS / "sa_app" / "backend" / "vendor" / "astrolog" / "ast77src"
)
LISTOK_AST77 = PROJECTS / "ast77src"
LISTOK_BINARY = PROJECTS / "listok" / "astrolog"


def resolve_ast77_root() -> Path:
    for raw in (
        os.environ.get("AST77_ROOT", "").strip(),
        str(SA_APP_AST77),
        str(LISTOK_AST77),
    ):
        if not raw:
            continue
        root = Path(raw).expanduser().resolve()
        if (root / "astrolog-custom-tropical.as").is_file():
            return root
    raise FileNotFoundError(
        "ast77src not found. Set AST77_ROOT to sa_app/backend/vendor/astrolog/ast77src "
        "or ~/Projects/ast77src"
    )


def resolve_ast77_binary(root: Path) -> Path:
    for raw in (
        os.environ.get("AST77_BIN", "").strip(),
        str(root / "astrolog"),
        str(LISTOK_BINARY),
    ):
        if not raw:
            continue
        p = Path(raw).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return p
    raise FileNotFoundError(f"astrolog binary not found under {root}")


def astrolog_cfg() -> dict:
    root = resolve_ast77_root()
    binary = resolve_ast77_binary(root)
    return {"ast77_root": str(root), "ast77_binary": str(binary)}
