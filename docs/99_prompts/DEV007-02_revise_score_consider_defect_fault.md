# DEV007-02 Revise Score To Consider Detected Faults

## Objective

Revise swing v2 scoring so Detected Faults are explicitly accounted for in the
100-point score. The current implementation calculates metric deductions first, derives
Detected Faults mostly from those metric severities, and then calculates the overall
score from phase scores only. This means Detected Faults affect feedback,
improvement priorities, and drills, but they do not directly add score deductions.

The revised scoring model must make the relationship between metric deductions,
faults, phase scores, and the overall score explicit and testable. It must avoid double
counting a metric problem as both a metric deduction and a full independent fault
deduction, while ensuring fault evidence that is not currently represented as a scored
metric can still affect the score.

This task includes architecture, implementation, deterministic tests, documentation, and
verification. It is not a release or deployment task.

## Required Workflow

Follow the repository agent workflow in order:

1. `planning`
2. `architecture`
3. `coding`
4. `quality-assurance`
5. `final-review-planning`

Update `PLANS.md` during planning and final review. Do not stop after planning. Do not
run the release agent or create a release, deployment, Docker setup, hosted service,
package publication, version tag, or GitHub Release.

## Required Reading Before Coding

Read these files before implementation:

- `AGENTS.md`
- `PLANS.md`
- `.agents/skills/baseball-motion-analysis/SKILL.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- `docs/02_architecture/adr/ADR-0009-swing-evaluation-v2-baseline-replacement.md`
- `docs/02_architecture/adr/ADR-0011-swing-aspect-aware-measurement-space.md`
- `docs/02_architecture/adr/ADR-0012-enhanced-swing-pose-diagnostics.md`
- `docs/02_architecture/adr/ADR-0013-fps-independent-timestamp-sampling-and-analysis.md`
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Review the relevant implementation:

- `src/baseball_motion_analysis/analysis/swing.py`
- `src/baseball_motion_analysis/feedback/swing.py`
- `src/baseball_motion_analysis/app/swing_services.py`
- `src/baseball_motion_analysis/api/schemas.py`
- `src/baseball_motion_analysis/ui/web/static/app.js`
- `src/baseball_motion_analysis/ui/web/templates/index.html`

Review existing tests for every touched module, especially:

- `tests/unit/test_swing_analysis.py`
- `tests/unit/test_swing_feedback.py`
- `tests/unit/test_swing_motion_metrics.py`
- `tests/integration/test_swing_application_service.py`
- `tests/integration/test_swing_analysis_api.py`
- `tests/integration/test_swing_video_analysis_api.py`

## Confirmed Current Issue

Detected Faults are not currently direct scoring inputs.

Current flow in `src/baseball_motion_analysis/analysis/swing.py`:

```text
raw metrics
  -> evaluated metric severity and metric deduction
  -> detected faults
  -> phase scores from metric deductions
  -> overall score from phase scores
```

Detected Faults therefore affect:

- `analysis.detected_faults`
- `analysis.improvement_priorities`
- feedback improvement text
- drill suggestions
- browser result display

Detected Faults do not currently affect:

- `phase_scores`
- `overall_score`
- metric deductions

Most faults correlate with lower scores because they are derived from metrics that
already have deductions. However, some fault evidence is not represented as a scored
metric, such as:

- `wrist_chest_distance_ratio` evidence used by door swing / casting detection.
- `lead_knee_forward_drift_ratio` evidence used by collapsed lead side detection.

Those secondary evidence paths can make a fault visible without a clear score impact.
The revised model must close that gap.

## Required Outcomes

### 1. Define A Fault-Aware Scoring Model

Create a scoring model that explicitly describes how Detected Faults influence the
score.

Required behavior:

- Keep the public score on a 0 to 100 scale.
- Keep phase-weighted scoring or document any intentional replacement.
- Keep scoring in `analysis`, not in UI, API routes, storage, or feedback text.
- Account for fault severity, phase, confidence, and evidence availability.
- Ensure a fault can reduce the relevant phase score or a clearly named score adjustment.
- Ensure the overall score includes the fault-aware phase scores or adjustment.
- Cap deductions so one visible issue cannot drive the score below reasonable bounds
  multiple times through overlapping evidence.
- Keep missing or not-evaluated evidence as a confidence/limitation concern unless a
  real detected fault has enough evidence to score.
- Preserve skipped or unavailable impact behavior: if an impact-phase fault is
  suppressed because impact is skipped or unavailable, it must not add a hidden score
  penalty.

The architecture step must decide whether faults become:

- phase-level additional deductions,
- separate fault-adjustment deductions displayed alongside phase scores,
- metric-linked deductions with explicit fault contribution metadata,
- or another documented model.

Do not leave the relationship implicit.

### 2. Avoid Double Counting Metric-Backed Faults

Most current faults are summaries of one or more metric problems. The revised scoring
must not simply add a full independent fault penalty on top of every metric deduction.

Required behavior:

- Identify which metrics contributed to each fault.
- Decide and document whether metric-backed faults add no extra deduction, a capped
  incremental deduction, or a severity/confidence-scaled adjustment.
- Ensure secondary evidence that currently has no metric deduction can still influence
  score.
- Keep improvement priority ordering consistent with the final score contributors.
- Make fault-to-score behavior inspectable in tests and, if exposed publicly, in API/UI
  result data.

Examples to handle:

- Door swing / casting caused only by bad torso tilt, grip loading, or early connection
  should not be double-counted as a full extra fault penalty unless the scoring model
  explicitly caps and documents the incremental penalty.
- Door swing / casting caused by excessive wrist-to-chest distance should have a score
  impact even if the existing metrics are otherwise good.
- Collapsed lead side caused by lead knee forward drift should have a score impact even
  if the current lead-knee metric is not severe enough by itself.

### 3. Preserve Architecture Boundaries

Required ownership:

- `motion` may provide baseball movement measurements and phase semantics.
- `analysis` owns fault-aware scoring, thresholds, score deductions, and confidence.
- `feedback` converts returned analysis results into cautious language and drills.
- `app` orchestrates services and may expose browser-neutral score breakdown data.
- `api` serializes returned scoring fields without calculating baseball rules.
- `ui` renders score, faults, and explanations without owning scoring formulas.

Do not move baseball thresholds, fault scoring weights, severity mappings, or drill
decisions into browser JavaScript, API routes, templates, or storage adapters.

### 4. Update Result Data Deliberately

If the final design needs new fields, add them deliberately and document them.

Possible additions include:

- fault-level deduction or score impact
- linked metric names for each fault
- phase score metric deduction versus fault deduction
- total metric deduction and total fault adjustment
- a score-explanation structure suitable for API/UI rendering

Required behavior:

- Preserve backward-compatible existing fields where practical:
  - `overall_score`
  - `phase_scores`
  - `metrics`
  - `detected_faults`
  - `good_points`
  - `improvement_priorities`
  - `confidence`
  - `limitations`
- If API response schemas change, update integration tests and docs.
- Keep English/Japanese UI strings isolated if any visible labels are added.
- Do not expose absolute local paths or private media details.

### 5. Keep Feedback Cautious And Score-Consistent

Feedback should reflect the same issues that affected the score.

Required behavior:

- Improvement points should remain fault-first when detected faults exist.
- Drill suggestions should remain tied to detected fault patterns.
- If a detected fault meaningfully lowered the score, feedback should make that
  understandable without overclaiming.
- If a detected fault is low confidence and has a small score impact, feedback should
  preserve cautious language.
- Do not introduce medical, injury, or guaranteed coaching claims.

## Architecture Requirements

- Add a new ADR under `docs/02_architecture/adr/` for fault-aware swing scoring, or
  update an existing accepted ADR only if the decision is clearly a small amendment.
- Document how metric deductions, fault deductions or adjustments, phase scores, and
  overall score compose.
- Document how double counting is avoided.
- Document how unscored secondary fault evidence becomes score-relevant.
- Document how confidence affects fault scoring.
- Document API/schema implications, including any migration risks.

## Testing Requirements

Use deterministic synthetic poses and existing test helpers. Tests must not require
private user videos, external services, credentials, model downloads, or heavy binary
assets.

### Analysis Unit Tests

Add or update tests proving:

- A good swing still scores near 100 and emits no detected faults.
- Each existing fault candidate can affect the final score through the documented model.
- A metric-backed fault does not receive an uncapped duplicate full penalty.
- A fault triggered by secondary evidence with otherwise acceptable metrics reduces the
  relevant score according to the documented model.
- Severe faults reduce score more than warning faults when confidence is comparable.
- Low-confidence fault evidence has lower score impact than high-confidence fault
  evidence, or is represented through confidence if the ADR chooses that model.
- Skipped or unavailable impact suppresses impact-phase faults and hidden impact-fault
  penalties.
- Missing/not-evaluated metrics reduce confidence and limitations rather than silently
  adding full fault penalties.
- Phase scores and overall score remain bounded between 0 and 100.
- Improvement priorities align with the highest-impact score contributors.

### Application And API Tests

Add or update tests proving:

- `SwingAnalysisApplicationService` returns the revised score breakdown.
- Stored-video swing analysis preserves the same score semantics.
- API schemas serialize any new score-impact fields without calculating scoring rules.
- Existing clients still receive `overall_score`, `phase_scores`, `metrics`, and
  `detected_faults`.

### Feedback And UI Tests

Add or update tests proving:

- Feedback improvement points and drills remain fault-based.
- The browser displays any new score-impact labels or explanation fields without owning
  scoring formulas.
- English and Japanese localization entries are present for new UI labels, if added.
- Existing result layout order is preserved unless the plan explicitly changes it.

## Documentation Requirements

Update:

- `PLANS.md`
- `docs/01_product/feature_catalog.md`
- `docs/02_architecture/system_overview.md`
- a new or amended ADR under `docs/02_architecture/adr/`
- `docs/03_development_log/` with a dated Obsidian-compatible entry
- `docs/04_motion_knowledge/swing.md`
- `docs/05_manuals/swing_motion_analysis_ui.md`

Documentation must explain:

- Detected Faults are now score-relevant.
- How metric deductions and fault adjustments compose.
- How duplicate penalties are avoided.
- How secondary fault evidence affects scoring.
- How confidence changes score interpretation.
- How users should interpret score, phase scores, metrics, detected faults, feedback,
  and limitations together.

## Non-Goals

- Do not add bat, barrel, ball, or exact contact detection.
- Do not add new swing fault categories unless required to make existing scoring
  explainable.
- Do not redesign swing event detection, pose estimation, video sampling, timestamp
  policy, replay overlays, or MediaPipe configuration.
- Do not change fielding, throwing, or pitching analysis.
- Do not move scoring formulas into UI, API, storage, or feedback layers.
- Do not add hosted services, cloud upload, telemetry, deployment, Docker, mobile
  adapters, authentication, PyPI publishing, or release work.
- Do not commit videos, model files, generated reports, `.env` files, credentials, or
  heavy fixtures.

## Acceptance Criteria

- Detected Faults have an explicit, documented relationship to score.
- Secondary fault evidence that is not currently a scored metric can lower the relevant
  score when the detected fault is sufficiently supported.
- Metric-backed faults do not cause uncontrolled double counting.
- Phase scores and overall score are computed from the documented model and remain
  bounded from 0 to 100.
- Confidence and limitations still distinguish weak evidence from confirmed issues.
- Impact-phase fault penalties are not applied when impact faults are suppressed by
  skipped or unavailable impact status.
- Application service and API responses expose any required score-impact information
  without moving scoring logic outside `analysis`.
- Browser UI renders any new score explanation data without calculating baseball rules.
- Feedback remains cautious and consistent with score contributors.
- Unit, integration, API, feedback, and UI tests cover the new semantics.
- Relevant docs are updated.
- Required quality gates pass.
- Final planning review reports no blocking issue.
- No release or deployment is created.

## Quality Gates

Run after coding:

```bash
node --check src/baseball_motion_analysis/ui/web/static/app.js
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

If formatting is needed:

```bash
uv run ruff format .
```

Do not declare the task complete if fault-aware scoring tests, API/schema tests, feedback
tests, UI tests for any new display behavior, or required repository quality gates fail.

## Final Review Notes To Capture

During `final-review-planning`, confirm:

- The selected fault-aware scoring model is documented in an ADR.
- Each detected fault has a clear score-impact rule or explicit no-extra-deduction rule.
- Secondary evidence paths have score coverage.
- Double counting is capped or otherwise prevented.
- Score, confidence, feedback, drills, and limitations tell a consistent story.
- UI/API layers do not contain baseball scoring formulas.
- Tests cover normal, warning, severe, low-confidence, skipped-impact, secondary-evidence,
  and missing-evidence cases.
- All required quality gates pass.
- No secrets, private media, large videos, model files, generated reports, or unrelated
  user changes are included.
- No release or deployment was created.
