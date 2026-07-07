---
id: corporate-agency
name: Meridian — corporate / agency
domain: agency, corporate, consulting, business, services, studio, агентство, компания, консалтинг, услуги, бизнес, студия
style: professional, clean, trustworthy, modern, профессионал, корпоратив
colors: blue, navy, neutral, син, темно-син
tags: agency, corporate, consulting, business, services, studio, professional, team, cases, contact, агентство, компания, услуги, консалтинг, команда, кейсы
stack: html, tailwind
summary: Professional navy corporate/agency site — services grid, case highlights, team, CTA.
---

# Meridian — corporate / agency
For agencies, consultancies, B2B service firms, studios. Trust-building, structured,
professional — not flashy.

## Tokens
bg `#FFF` · alt `#F5F7FA` · text `#0F1B2D` · muted `#5A6B7F` · primary `#1F4FD8` ·
navy `#0F1B2D` · border `#E2E8F0`. Font Inter; headings semibold. h1 clamp(2.2rem,5vw,3.5rem).
Cards `rounded-2xl border`. Sections `py-20`. Restrained blue accent on navy/white base.

## Layout order
nav (logo + links + "Contact") → hero (clear value prop + CTA + trust logos) →
services (3–4 col grid) → featured case (split image + result stat) → team → CTA band → footer.

## Snippets
Hero + services:
```html
<section class="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
  <h1 class="text-4xl md:text-5xl font-semibold text-[#0F1B2D] max-w-3xl mx-auto">We help companies grow with clarity.</h1>
  <p class="mt-5 text-[#5A6B7F] max-w-xl mx-auto">Strategy, design and engineering under one roof.</p>
  <a class="inline-block mt-8 px-6 py-3 rounded-lg bg-[#1F4FD8] text-white hover:bg-[#183FB0]">Book a call</a>
</section>
<section class="max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
  <div class="rounded-2xl border border-[#E2E8F0] p-6"><!-- repeat -->
    <div class="w-10 h-10 rounded-lg bg-[#EEF3FF] text-[#1F4FD8] grid place-items-center mb-4">◆</div>
    <h3 class="font-semibold text-[#0F1B2D]">Strategy</h3>
    <p class="text-sm text-[#5A6B7F] mt-2">Research-led roadmaps that ship.</p></div>
</section>
```
Featured case with result stat:
```html
<section class="bg-[#0F1B2D] text-white"><div class="max-w-6xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
  <div class="aspect-video bg-white/10 rounded-2xl"></div>
  <div><p class="text-sm text-[#8FB0FF]">Case study</p>
    <h2 class="text-3xl font-semibold mt-2">Rebuilt checkout for Northwind</h2>
    <p class="mt-3 text-white/70">A focused 8-week engagement.</p>
    <p class="mt-6 text-4xl font-semibold">+38%<span class="text-base text-white/60 ml-2">conversion</span></p></div>
</div></section>
```

## Adaptation
Lead with a clear value proposition, not a slogan. Services grid + a case study with a hard
result number are mandatory (proof sells B2B). Navy + one blue accent; swap to client brand
color only for the primary. Keep it structured and calm.
