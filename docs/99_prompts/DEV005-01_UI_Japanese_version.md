# DEV005-01: Japanese UI Version

## Purpose

Plan a Japanese UI version for `baseball_motion_analysis` while keeping English as the
default language and preserving the local-PC-first, service-oriented architecture.

The Japanese version should be implemented as localization/i18n support in the same UI,
not as a separate application or fork.

## Language Direction

English is the default language.

Japanese may be added later as a selectable UI language. The initial implementation
should keep user-facing text isolated so Japanese translations can be added without
rewriting domain logic, analysis rules, storage behavior, or application services.

## Scope

- Keep English as the default UI language.
- Add a language selector, for example `English / 日本語`, that enables switching
  languages in the same UI.
- Support Japanese labels, buttons, validation messages, analysis status text, and
  report text through a localization layer.
- Keep the selected language as UI state or local user preference.
- Render analysis results in the selected language when localized feedback templates are
  available.

## Non-Goals

- Do not create a separate Japanese-only application.
- Do not duplicate domain, analysis, storage, or application-service code for Japanese.
- Do not hard-code Japanese or English strings inside baseball motion rules.
- Do not change motion scoring behavior based on UI language.
- Do not add hosted translation services or external uploads for translation.

## Architecture Requirements

The same application-service outputs should support both languages. Internal analysis
results should remain structured and language-independent, using stable identifiers such
as issue codes, metric names, scores, confidence values, and limitations.

User-facing text should be generated or rendered through the UI and feedback localization
layer. Domain logic, analysis rules, storage, video handling, pose estimation, and
application services must not depend on the selected language.

Recommended flow:

```text
analysis result codes and structured findings
  -> feedback/UI localization layer
  -> English or Japanese user-facing text
```

## Acceptance Criteria

- English remains the default UI language.
- The UI includes a visible language selector such as `English / 日本語`.
- Switching language changes user-facing UI text without rerunning analysis.
- Japanese analysis-result text can be rendered from structured results or feedback
  templates.
- Domain logic, analysis rules, storage, and application services stay
  language-independent.
- Tests cover language selection behavior and confirm core analysis output is not tied
  to UI language.

## Risks

- Hard-coded strings may make later translation expensive.
- Analysis feedback may become inconsistent if English and Japanese templates are not
  maintained together.
- Japanese baseball terms should be reviewed for clarity for players, coaches, and
  parents.
- Some UI elements may need responsive layout adjustments because Japanese text length
  differs from English.
