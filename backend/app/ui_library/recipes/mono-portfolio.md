---
id: mono-portfolio
name: Slate — monochrome portfolio
domain: portfolio, personal, resume, freelance, designer, photographer, портфолио, резюме, фрилансер, дизайнер
style: minimal, monochrome, editorial, typographic, минимал, чист
colors: monochrome, black, white, mono, черн, бел
tags: portfolio, personal, resume, freelance, designer, photographer, minimal, mono, case, work, портфолио, резюме, фрилансер, дизайнер, работы
stack: html, tailwind
summary: Black-on-white typographic portfolio — big name, project list, case studies, contact.
---

# Slate — monochrome portfolio
For personal/creative portfolios: designer, dev, photographer, freelancer. Type-driven,
near-monochrome, projects are the hero.

## Tokens
bg `#FFF` · text `#111` · muted `#777` · border `#E5E5E5` · accent `#111` (invert on hover).
One sans (Inter/Geist) or grotesk. Huge display: name clamp(2.5rem,8vw,6rem), tight leading.
Container `max-w-4xl mx-auto px-6`. Lots of whitespace. Underline links on hover. No color
unless one restrained accent. Radius `rounded-none`.

## Layout order
minimal nav (name + 2 links) → intro (one bold sentence about what you do) →
selected work (list rows: title · year · role, hover reveals thumb) → about → contact (big mailto).

## Snippets
Intro + work list:
```html
<header class="max-w-4xl mx-auto px-6 py-6 flex justify-between text-sm">
  <a class="font-medium">Alex Slate</a><nav class="flex gap-6 text-[#777]"><a class="hover:text-black">Work</a><a class="hover:text-black">About</a></nav>
</header>
<section class="max-w-4xl mx-auto px-6 pt-16 pb-24">
  <h1 class="text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05]">Product designer building calm, useful interfaces.</h1>
</section>
<section class="max-w-4xl mx-auto px-6 border-t border-[#E5E5E5]">
  <a class="group flex items-baseline justify-between py-6 border-b border-[#E5E5E5]"><!-- repeat -->
    <span class="text-2xl group-hover:pl-2 transition-all">Northwind Dashboard</span>
    <span class="text-sm text-[#777]">2024 · Lead</span></a>
</section>
```
Contact:
```html
<section class="max-w-4xl mx-auto px-6 py-24">
  <p class="text-sm text-[#777] mb-4">Get in touch</p>
  <a href="mailto:hi@slate.com" class="text-3xl md:text-5xl font-semibold underline decoration-1 underline-offset-8 hover:text-[#777]">hi@slate.com</a>
</section>
```

## Adaptation
Keep it near-monochrome; at most one accent color if client insists. Work list rows are the
core — title + year + role, hover reveals thumbnail or shifts text. Never add gradients,
cards, or shadows. One font, huge display headline.
