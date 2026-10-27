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
from tests.test_directed_aspects import (
    test_ft_neg_alternate_mercury_square_uranus_exists,
    test_dk_neg_converse_chiron_square_radix_mercury_directed,
)
test_ft_neg_pos_converse_utc()
test_inc_neg_pos_converse_utc()
test_dk_neg_pos_converse_utc()
test_spot_checks_hardcoded()
test_ft_neg_spot_longitudes()
test_ft_neg_alternate_mercury_square_uranus_exists()
test_dk_neg_converse_chiron_square_radix_mercury_directed()
print("OK: converse timestamps + Zet spot checks + directed Phase C")
PY

EARNINGS_PY="${STUDY}/.venv/bin/python"
if [[ -x "$EARNINGS_PY" ]]; then
  export PYTHONPATH="${ROOT}:${ROOT}/SWEP/src:${STUDY}:${STUDY}/.venv/lib/python3.15/site-packages"
  export STUDY
  "$EARNINGS_PY" - <<PY
import sys
from pathlib import Path
sys.path.insert(0, "${STUDY}")
import importlib.util
STUDY = Path("${STUDY}")
for mod_name in ("test_earnings_pipeline", "test_daily_panel", "test_phase_h", "test_phase_i", "test_cross_company", "test_cross_company_v2"):
    spec = importlib.util.spec_from_file_location(mod_name, STUDY / "tests" / f"{mod_name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    for attr in sorted(dir(mod)):
        if attr.startswith("test_"):
            getattr(mod, attr)()
print("OK: earnings + daily pipeline tests")
PY
fi
