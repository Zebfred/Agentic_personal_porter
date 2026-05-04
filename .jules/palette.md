## 2026-05-04 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found that multiple navigation buttons (`#prev-month-btn`, `#next-month-btn`, `#close-modal-btn`) in the frontend used icons (◀, ▶, &lt;, &gt;, &times;) without screen reader accessible labels, making navigation difficult for visually impaired users.
**Action:** Added `aria-label` attributes to all icon-only buttons to improve accessibility without changing visual UI.
