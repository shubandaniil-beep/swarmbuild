---
id: accordion-faq
name: Accordion / FAQ
kind: component
triggers: faq, accordion, aккордеон, вопрос, часто задаваем, раскрыва, спойлер, q&a
summary: Expand/collapse FAQ list using native details/summary — zero-JS, accessible.
---

# Component: Accordion / FAQ
FAQ or any expand/collapse list. Uses native `<details>` so it works without JS and is
accessible by default. Recolor to page tokens.

```html
<section class="max-w-2xl mx-auto px-6 py-16">
  <h2 class="text-2xl font-semibold mb-6">Frequently asked</h2>
  <div class="divide-y border-y">
    <details class="group py-4"><!-- repeat per Q -->
      <summary class="flex justify-between items-center cursor-pointer list-none font-medium">
        How does the free trial work?
        <span class="transition group-open:rotate-45 text-xl leading-none">+</span>
      </summary>
      <p class="mt-3 text-sm text-gray-600">14 days, no card required. Cancel anytime.</p>
    </details>
  </div>
</section>
```

Usage: add a `<details>` block per question; `list-none` + the `group-open:rotate-45`
span gives the +/× toggle. Add `open` to the first item to show it expanded. For a
single-open-at-a-time behavior, give each `<details name="faq">` the same `name`.
React: map items to state or use the same `<details>` markup directly.
