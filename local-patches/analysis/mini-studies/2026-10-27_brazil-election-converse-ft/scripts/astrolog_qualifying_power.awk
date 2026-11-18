#!/usr/bin/env awk -f
# Sum qualifying aspect power (Sun–Pluto both endpoints) from astrolog -a dumps.
# Usage: awk -f scripts/astrolog_qualifying_power.awk output/astrolog_debug/*_2026-10-26_c2r.txt
BEGIN {
  p="^(Sun|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto)$"
}
/- power:/ {
  split($0, a, /[)\]][[:space:]]+/)
  right=a[3]
  sub(/[[:space:]]*- orb:.*/, "", right)
  gsub(/^[[:space:]]+|[[:space:]]+$/, "", right)
  if ($2 ~ p && right ~ p) {
    sum += $NF
    n++
  }
}
END {
  printf "Count: %d | Sum: %.4f | Avg: %.4f\n", n, sum, n ? sum/n : 0
}
