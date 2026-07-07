---
id: saas-light
name: Clarity — light SaaS
domain: saas, app, software, tool, b2b, productivity, startup, сервис, приложение, софт, инструмент, продуктивность
style: clean, light, friendly, modern, professional, чист, светл, современ
colors: light, blue, white, indigo, светл, син, бел
tags: saas, light, app, software, tool, b2b, productivity, features, pricing, signup, сервис, приложение, светл, тариф, регистрация, инструмент
stack: html, tailwind
summary: Bright, clean light-theme SaaS landing — screenshot hero, feature grid, pricing, signup.
---

# Clarity — light SaaS
The bright alternative to dark-saas: for SaaS/tools that want approachable, clean, trustworthy.
Use when the brief is a SaaS/app but NOT "dark/edgy".

## Tokens
bg `#FFF` · alt `#F8FAFC` · text `#0F172A` · muted `#64748B` · primary `#4F46E5` (indigo) ·
accent `#0EA5E9` · border `#E7EAF0`. Font Inter. Cards `rounded-2xl border shadow-sm`.
Soft `#F8FAFC` section bands to separate. h1 clamp(2.4rem,5vw,3.75rem). Subtle, not flashy.

## Layout order
nav (+ "Sign up") → hero (headline + subcopy + dual CTA + big product screenshot) → logo cloud →
3-col feature grid → feature split (image + bullets) → pricing (3 tiers, middle highlighted) →
testimonial → CTA band → footer.

## Snippets
Hero:
```html
<section class="max-w-5xl mx-auto px-6 pt-20 pb-12 text-center">
  <h1 class="text-4xl md:text-6xl font-bold text-[#0F172A] tracking-tight">The simplest way to run your team.</h1>
  <p class="mt-5 text-lg text-[#64748B] max-w-xl mx-auto">Plan, track and ship — without the busywork.</p>
  <div class="mt-8 flex gap-3 justify-center">
    <a class="px-6 py-3 rounded-xl bg-[#4F46E5] text-white font-medium">Start free</a>
    <a class="px-6 py-3 rounded-xl border border-[#E7EAF0] text-[#0F172A]">See how it works</a></div>
  <div class="mt-14 aspect-video max-w-4xl mx-auto rounded-2xl border border-[#E7EAF0] shadow-sm bg-[#F8FAFC]"></div>
</section>
```
Feature card + highlighted price tier:
```html
<div class="rounded-2xl border border-[#E7EAF0] bg-white shadow-sm p-6"><!-- feature -->
  <div class="w-10 h-10 rounded-lg bg-[#EEF0FE] text-[#4F46E5] grid place-items-center mb-4">◇</div>
  <h3 class="font-semibold text-[#0F172A]">Automations</h3><p class="text-sm text-[#64748B] mt-2">Let the busywork run itself.</p></div>
<div class="rounded-2xl border-2 border-[#4F46E5] bg-white p-6 relative shadow-sm"><!-- middle tier -->
  <span class="absolute -top-3 left-6 text-xs bg-[#4F46E5] text-white px-2 py-0.5 rounded-full">Popular</span>
  <h3 class="text-[#0F172A]">Pro</h3><p class="text-3xl font-bold mt-2">$19</p>
  <a class="block text-center mt-6 px-4 py-2 rounded-lg bg-[#4F46E5] text-white font-medium">Choose Pro</a></div>
```

## Adaptation
Product screenshot placeholder in the hero is mandatory. Middle pricing tier highlighted (border
+ Popular badge). Use `#F8FAFC` bands to break up sections. Keep it light, clean, indigo accent —
recolor primary only for a brand color. This is the go-to for a generic SaaS brief.
