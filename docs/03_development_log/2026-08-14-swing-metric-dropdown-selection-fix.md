# 2026-08-14 Swing Metric Dropdown Selection Fix

## Context

The compact `Metric` dropdown added for DEV004-07 could open, but selecting a specific
metric did not work. `All metrics` stayed selected and the UI immediately returned to the
all-metrics state.

## Root Cause

The checkbox change handler collected every checked checkbox. Because `All metrics` is
checked whenever no specific metric is selected, clicking a specific metric produced a
checked set that still included `All metrics`. The handler interpreted that as the
all-metrics/default state and cleared the specific selection.

## Fix

* Updated the metric dropdown change handler to pass the changed checkbox into the
  selection-sync function.
* If `All metrics` is changed, the selected metric set is cleared.
* If a specific metric is checked, that metric is added and `All metrics` is unchecked by
  the normal sync step.
* If a specific metric is unchecked, that metric is removed; if no specific metrics
  remain, the normal sync step restores `All metrics`.
* Added static integration coverage for the changed-checkbox selection path.

## Verification

* The fix remains browser-only and does not change service/API contracts.
* No release or deployment was created.
