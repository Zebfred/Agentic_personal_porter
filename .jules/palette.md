## 2026-05-04 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found that multiple navigation buttons (`#prev-month-btn`, `#next-month-btn`, `#close-modal-btn`) in the frontend used icons (◀, ▶, &lt;, &gt;, &times;) without screen reader accessible labels, making navigation difficult for visually impaired users.
**Action:** Added `aria-label` attributes to all icon-only buttons to improve accessibility without changing visual UI.
## 2024-04-27 - Icon-only buttons lacking ARIA labels
**Learning:** Found several icon-only buttons (like `&lt;` `&gt;` and `&times;` for calendar navigation and modal closing) that lacked accessibility context for screen readers.
**Action:** Always verify that buttons containing only text-symbols or icons have a descriptive `aria-label` attribute so their function is clear to assistive technologies.
## 2024-05-18 - Fix custom toggle inputs visually hidden

**Learning:** Custom UI toggle checkboxes visually hide the actual `<input>` using classes like `.sr-only`, breaking default keyboard focus rings.
**Action:** When working with hidden form elements, ensure keyboard accessibility by targeting focus on the hidden input using the `:focus-visible` pseudo-class and applying styles to its visible sibling element (e.g., `#input:focus-visible + #visible-bg { outline: 2px solid; }`), and add ARIA attributes to describe its state.
## 2024-05-19 - Explicit 'for' attributes missing on labels
**Learning:** Found multiple instances where `<label>` tags either didn't have a `for` attribute matching their input's `id` or were missing altogether (requiring visually hidden `.sr-only` labels). This makes it harder for screen readers to associate text with inputs, and prevents users from clicking the label text to activate the input.
**Action:** Always ensure every `<input>` has a `<label>` with a matching `for` attribute. Add `.sr-only` if the label shouldn't be visually displayed. Add the Tailwind `cursor-pointer` class to the label to indicate interactivity.
## 2024-05-19 - Ensure textareas have labels
**Learning:** Textareas generated dynamically in JavaScript (like the gap-input textarea in user_hub.js) lacked associated labels, making them invisible to screen readers or confusing for assistive tech.
**Action:** Always ensure every `<textarea>` element, not just `<input>` elements, has an explicit `<label>` with a matching `for` attribute. Use `.sr-only` if the label shouldn't be visually displayed.
