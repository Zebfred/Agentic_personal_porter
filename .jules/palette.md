## 2024-04-27 - Icon-only buttons lacking ARIA labels
**Learning:** Found several icon-only buttons (like `&lt;` `&gt;` and `&times;` for calendar navigation and modal closing) that lacked accessibility context for screen readers.
**Action:** Always verify that buttons containing only text-symbols or icons have a descriptive `aria-label` attribute so their function is clear to assistive technologies.
