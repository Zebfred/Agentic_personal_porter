## 2026-05-04 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found that multiple navigation buttons (`#prev-month-btn`, `#next-month-btn`, `#close-modal-btn`) in the frontend used icons (◀, ▶, &lt;, &gt;, &times;) without screen reader accessible labels, making navigation difficult for visually impaired users.
**Action:** Added `aria-label` attributes to all icon-only buttons to improve accessibility without changing visual UI.
## 2024-04-27 - Icon-only buttons lacking ARIA labels
**Learning:** Found several icon-only buttons (like `&lt;` `&gt;` and `&times;` for calendar navigation and modal closing) that lacked accessibility context for screen readers.
**Action:** Always verify that buttons containing only text-symbols or icons have a descriptive `aria-label` attribute so their function is clear to assistive technologies.
## 2024-05-18 - Fix custom toggle inputs visually hidden

**Learning:** Custom UI toggle checkboxes visually hide the actual `<input>` using classes like `.sr-only`, breaking default keyboard focus rings.
**Action:** When working with hidden form elements, ensure keyboard accessibility by targeting focus on the hidden input using the `:focus-visible` pseudo-class and applying styles to its visible sibling element (e.g., `#input:focus-visible + #visible-bg { outline: 2px solid; }`), and add ARIA attributes to describe its state.
## 2024-05-18 - Missing label tags on UI inputs

**Learning:** Found `<input>` elements (checkboxes, text inputs, date pickers) that were missing an explicit `<label>` tag with a matching `for` attribute, causing issues for screen readers and reducing the clickable area for users.
**Action:** Always ensure that every `<input>` has a properly associated `<label>` element. Use visually hidden (`.sr-only`) labels when visual layout doesn't require text, and link text using `for="inputId"` to increase the click area.
