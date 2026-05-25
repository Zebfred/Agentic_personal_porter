## 2026-05-04 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found that multiple navigation buttons (`#prev-month-btn`, `#next-month-btn`, `#close-modal-btn`) in the frontend used icons (◀, ▶, &lt;, &gt;, &times;) without screen reader accessible labels, making navigation difficult for visually impaired users.
**Action:** Added `aria-label` attributes to all icon-only buttons to improve accessibility without changing visual UI.
## 2024-04-27 - Icon-only buttons lacking ARIA labels
**Learning:** Found several icon-only buttons (like `&lt;` `&gt;` and `&times;` for calendar navigation and modal closing) that lacked accessibility context for screen readers.
**Action:** Always verify that buttons containing only text-symbols or icons have a descriptive `aria-label` attribute so their function is clear to assistive technologies.
## 2024-05-18 - Fix custom toggle inputs visually hidden

**Learning:** Custom UI toggle checkboxes visually hide the actual `<input>` using classes like `.sr-only`, breaking default keyboard focus rings.
**Action:** When working with hidden form elements, ensure keyboard accessibility by targeting focus on the hidden input using the `:focus-visible` pseudo-class and applying styles to its visible sibling element (e.g., `#input:focus-visible + #visible-bg { outline: 2px solid; }`), and add ARIA attributes to describe its state.

## 2026-05-04 - Fix Custom Label Interactive UI
**Learning:** Found multiple instances where labels were disconnected from input checkboxes (using `<span>` instead of `<label>`, missing `for` attributes, or missing unique `id` fields). Additionally, some interactive inputs/labels lacked visual indicators for interactivity.
**Action:** Replaced `<span>` wrappers with semantically correct `<label for="...">` elements tied to unique input `id`s to ensure screen reader focus. Added `cursor-pointer` to both inputs and their corresponding labels to clearly communicate interactivity.
