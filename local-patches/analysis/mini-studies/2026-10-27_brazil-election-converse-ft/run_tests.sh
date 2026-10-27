#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STUDY="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${ROOT}:${ROOT}/SWEP/src:${STUDY}:${STUDY}/../2026-10-26_uber-converse-cohort"
python3 "${STUDY}/tests/test_brazil_converse.py"
python3 "${STUDY}/tests/test_br2_historical.py"
