# DEV007-03 Weight Change

## Objective

Revise swing v2 phase scoring weights to slightly increase setup, stride, and foot
strike emphasis while reducing impact weighting.

## Requested Phase Weights

| Phase | Current Weight | Requested Weight |
| --- | ---: | ---: |
| Setup | 10% | 15% |
| Stride | 20% | 25% |
| Foot Strike | 25% | 25% |
| Impact | 35% | 25% |
| Follow-through | 10% | 10% |

The requested weights sum to 100%.

## Required Behavior

- Update swing v2 phase scoring weights in the `analysis` layer.
- Keep the scoring model on a 0 to 100 scale.
- Preserve DEV007-02 fault-aware scoring semantics:
  - metric deductions are credited first,
  - detected fault deductions are capped by phase, severity, and confidence,
  - linked metric deductions prevent uncontrolled double counting.
- Recalculate phase scores and overall score using the new weights.
- Ensure metric deductions and fault deductions still use the updated phase point budget.
- Keep UI and API adapters as render/serialization layers only; do not move scoring
  weights into browser JavaScript, templates, API routes, or storage adapters.

## Expected Impact

- Setup-related issues have more influence on overall score.
- Stride-related issues have more influence on overall score.
- Foot-strike influence stays the same as the current model.
- Impact-related issues have less influence than before.
- Follow-through influence stays unchanged.

## Required Updates

- `src/baseball_motion_analysis/analysis/swing.py`
- Unit tests for phase weights, metric deductions, fault deductions, and overall score.
- API/application tests if expected serialized values change.
- Documentation:
  - `PLANS.md`
  - `docs/04_motion_knowledge/swing.md`
  - `docs/05_manuals/swing_motion_analysis_ui.md`
  - architecture docs or ADR update if the weight change is treated as a scoring
    decision.

## Non-Goals

- Do not change swing phase detection.
- Do not change pose estimation, video sampling, replay overlays, or MediaPipe settings.
- Do not add new detected fault categories.
- Do not change fielding, throwing, or pitching analysis.
- Do not create a release or deployment.

## Acceptance Criteria

- Phase weights are exactly:
  - Setup: `0.15`
  - Stride: `0.25`
  - Foot Strike: `0.25`
  - Impact: `0.25`
  - Follow-through: `0.10`
- Weights sum to `1.0`.
- Overall score uses the new weighted phase scores.
- Metric and fault deductions reflect the updated phase budgets.
- Tests and documentation are updated.
- Required quality gates pass before completion.
