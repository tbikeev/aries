#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STUDY="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="${ROOT}:${ROOT}/SWEP/src:${STUDY}"
python3 "${STUDY}/tests/test_converse_timestamps.py" 2>/dev/null || true
python3 - <<'PY'
import sys, os
sys.path[:0] = [os.environ["PYTHONPATH"].split(":")[-1], os.environ["PYTHONPATH"].split(":")[0], os.environ["PYTHONPATH"].split(":")[1]]
from tests.test_converse_timestamps import (
    test_ft_neg_pos_converse_utc,
    test_inc_neg_pos_converse_utc,
    test_dk_neg_pos_converse_utc,
)
from tests.test_zet_fixtures import test_spot_checks_hardcoded, test_ft_neg_spot_longitudes
test_ft_neg_pos_converse_utc()
test_inc_neg_pos_converse_utc()
test_dk_neg_pos_converse_utc()
test_spot_checks_hardcoded()
test_ft_neg_spot_longitudes()
print("OK: converse timestamps + Zet spot checks")
PY
