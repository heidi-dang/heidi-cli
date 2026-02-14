## 2025-05-15 - Systemic Reliance on Title Attributes
**Learning:** This codebase relies heavily on the `title` attribute for tooltips on icon-only buttons, which provides poor accessibility for screen readers compared to `aria-label`.
**Action:** When touching icon-only interactive elements in this app, always supplement `title` with `aria-label` to ensure the action is announced effectively to assistive technology.
