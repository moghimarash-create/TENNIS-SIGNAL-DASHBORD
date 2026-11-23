---
name: Geomancy figure table & signal-map calibration
description: How the GEOMANCY_FIGURES parity→name table maps to standard geomancy, and the calibration caveat for GEO_SIGNAL_MAP after the table was corrected.
---

# Geomancy figure table (step4_search_signals.py)

`figure_from_elements(fire,air,water,earth)` builds a parity tuple `(n%2 ...)` (odd=1/single dot, even=0/double dot) in **fire→air→water→earth** order and looks it up in `GEOMANCY_FIGURES`. The table now follows **standard geomancy** (e.g. `(0,1,1,1)=Caput_Draconis`, `(1,1,1,0)=Cauda_Draconis`). An earlier version had 14 of 16 entries mislabeled (only Via=1111 and Populus=0000 were right).

**Why:** the original table was scrambled — not a clean swap or single transform. Confirmed against standard dot-structure: each line single(1)/double(2), figure = parity per element.

**How to apply:**
- Figure names are **display/scoring only** — matching never depends on them, so relabeling does NOT change which rows match. `verify_logic.py` match-set check is unaffected (stays 0 discrepancies); GEO-FIG / per-row / ELEM-TRIGGER checks recompute from the same table so they self-validate.
- Spelling: keep **`Conjunctio`** (not classical `Coniunctio`) — `GEO_SIGNAL_MAP` keys and `BEARISH_FIGURES` use `Conjunctio`. Any rename must update all three in lockstep or that figure silently drops out of its family/multiplier.
- Invariant to preserve: every name in `BULLISH_FIGURES`, `BEARISH_FIGURES`, and `GEO_SIGNAL_MAP` keys must exist as a value in `GEOMANCY_FIGURES`.

## GEO_SIGNAL_MAP calibration caveat
`GEO_SIGNAL_MAP[(figure,quadrant)]` multipliers (the 4 notable combos: Albus/SANGUINE, Acquisitio/PHLEGMATIC, Acquisitio/MELANCHOLIC, Conjunctio/PHLEGMATIC) were empirically tuned **against the OLD (incorrect) figure labels**. After the table correction, those multipliers now attach to the correctly-named figures, which may not be the figures the percentages were derived from. If geo-multiplier accuracy matters, re-derive `GEO_SIGNAL_MAP` from history under the corrected mapping. This only re-weights SCORE/SCORE_OVERALL/SCORE_CONF and the FIG nB/mb tally — never the match set.
