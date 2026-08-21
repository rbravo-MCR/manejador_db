# AGENTS.md

## Project

Backend Development IDE desktop application.

## Core rules

- Respect the modular architecture.
- Keep business logic out of PySide6 UI components.
- Preserve the Universal Schema Model as the central domain abstraction.
- Keep database-specific logic inside adapters, inspectors, and dialects.
- Generators must consume the Universal Schema Model.
- Do not overwrite user code without showing a diff first.
- Do not execute destructive database changes automatically.
- Add tests for core behavior.
- Do not introduce new frameworks without explaining the architectural reason.
- Prefer Python implementations first.
- Use Rust only for performance-sensitive components when justified by benchmarks.

## UX/UI

For UI work:

- Treat UX quality as part of the acceptance criteria.
- Keep the interface compact, professional, and developer-focused.
- Preserve high information density without clutter.
- Support Light and Dark themes.
- Use reusable components and centralized design tokens.
- Avoid oversized buttons, excessive rounded corners, and generic SaaS-dashboard styling.
- Validate visual hierarchy, spacing, alignment, hover/focus/disabled states, and keyboard usability.
- Do not consider UI work complete only because it compiles or tests pass.

- usar la skill ux-ui-desktop-ide
- mantener diseño compacto
- respetar dark/light
- usar componentes reutilizables
- validar visualmente cambios

## References

Follow the architecture and product requirements in:

- docs/PRODUCT_SPEC.md
- docs/ARCHITECTURE.md
- docs/ROADMAP.md
- docs/DECISIONS.md


