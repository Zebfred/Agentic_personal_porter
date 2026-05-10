## 2026-05-04 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found that multiple navigation buttons (`#prev-month-btn`, `#next-month-btn`, `#close-modal-btn`) in the frontend used icons (◀, ▶, &lt;, &gt;, &times;) without screen reader accessible labels, making navigation difficult for visually impaired users.
**Action:** Added `aria-label` attributes to all icon-only buttons to improve accessibility without changing visual UI.
## 2024-04-27 - Icon-only buttons lacking ARIA labels
**Learning:** Found several icon-only buttons (like `&lt;` `&gt;` and `&times;` for calendar navigation and modal closing) that lacked accessibility context for screen readers.
**Action:** Always verify that buttons containing only text-symbols or icons have a descriptive `aria-label` attribute so their function is clear to assistive technologies.
