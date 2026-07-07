---
id: dark-saas-landing
name: Nebula — dark SaaS landing
domain: saas, startup, software, app, b2b, tech, стартап, сервис, приложен, платформ
style: modern, dark, gradient, tech, sleek, темн, современ
colors: dark, violet, blue, neon, темн, син, фиолет
tags: dark, saas, landing, startup, tech, gradient, violet, indigo, hero, pricing, features, стартап, лендинг, темн, тариф, приложен
stack: html, tailwind
summary: Dark high-contrast SaaS landing, one violet→indigo gradient accent, features + pricing.
---

# Nebula — dark SaaS landing
For software/startup/B2B: app, API, dev tool, analytics. Dark bg, ONE gradient accent,
conversion-first.

## Tokens
bg `#0B0B12` · surface `#14141F` · border `#242433` · text `#F4F4F8` · muted `#9A9AB0` ·
gradient `linear-gradient(135deg,#7C5CFF,#4C6FFF)` · success `#3DDC97`.
Font Inter, tight tracking. h1 clamp(2.5rem,6vw,4.5rem). Cards `rounded-xl border`.
One gradient only: text accent + one CTA + faint hero backdrop. High contrast, no gray-on-gray.

## Layout order
nav → hero (badge, headline w/ gradient word, dual CTA, screenshot) → logo cloud →
3-col feature grid → feature split → pricing (3 tiers, middle highlighted) → CTA band → footer.

## Snippets
Nav + hero:
```html
<header class="border-b border-[#242433]"><nav class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
  <span class="font-semibold text-[#F4F4F8]">Nebula</span>
  <div class="hidden md:flex gap-8 text-sm text-[#9A9AB0]"><a class="hover:text-white">Features</a><a class="hover:text-white">Pricing</a></div>
  <a class="text-sm px-4 py-2 rounded-lg text-white" style="background:linear-gradient(135deg,#7C5CFF,#4C6FFF)">Get started</a>
</nav></header>
<section class="relative overflow-hidden">
  <div class="absolute inset-0 opacity-30 blur-3xl" style="background:radial-gradient(600px 300px at 50% 0%,#7C5CFF,transparent)"></div>
  <div class="relative max-w-4xl mx-auto px-6 pt-24 pb-16 text-center">
    <span class="inline-block text-xs px-3 py-1 rounded-full border border-[#242433] text-[#9A9AB0] mb-6">✦ v2 is live</span>
    <h1 class="text-4xl md:text-6xl font-semibold tracking-tight text-[#F4F4F8]">Ship faster with
      <span class="text-transparent bg-clip-text" style="background-image:linear-gradient(135deg,#7C5CFF,#4C6FFF)">less overhead</span>.</h1>
    <p class="mt-6 text-lg text-[#9A9AB0] max-w-xl mx-auto">Build, test, deploy. No config.</p>
    <div class="mt-8 flex gap-3 justify-center">
      <a class="px-6 py-3 rounded-lg text-white font-medium" style="background:linear-gradient(135deg,#7C5CFF,#4C6FFF)">Start free</a>
      <a class="px-6 py-3 rounded-lg border border-[#242433] text-[#F4F4F8] hover:bg-[#14141F]">Book a demo</a>
    </div>
  </div>
</section>
```
Feature card + highlighted price tier:
```html
<div class="rounded-xl border border-[#242433] bg-[#14141F] p-6">
  <div class="w-10 h-10 rounded-lg grid place-items-center mb-4" style="background:linear-gradient(135deg,#7C5CFF,#4C6FFF)">⚡</div>
  <h3 class="text-[#F4F4F8] font-medium mb-2">Instant deploys</h3><p class="text-sm text-[#9A9AB0]">Live in seconds, globally.</p></div>
<div class="rounded-xl p-6 relative" style="background:linear-gradient(135deg,#7C5CFF,#4C6FFF)">
  <span class="absolute -top-3 left-6 text-xs bg-white text-[#4C6FFF] px-2 py-0.5 rounded-full">Popular</span>
  <h3 class="text-white">Pro</h3><p class="text-3xl font-semibold text-white mt-2">$29</p>
  <a class="block text-center mt-6 px-4 py-2 rounded-lg bg-white text-[#4C6FFF] font-medium">Choose Pro</a></div>
```

## Adaptation
Keep dark bg + exactly one violet→indigo gradient (recolor only for a named brand color).
Middle pricing tier is always the gradient/highlighted one. Hero must have a product
screenshot placeholder — never a bare text hero.
