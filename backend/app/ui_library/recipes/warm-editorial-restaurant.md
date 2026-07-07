---
id: warm-editorial-restaurant
name: Ember — warm editorial restaurant
domain: restaurant, food, cafe, hospitality, bakery, bar, ресторан, кафе, еда, кухн, пекарн, бар
style: editorial, warm, elegant, cozy, magazine, тепл, уютн, элегант
colors: warm, terracotta, cream, amber, тепл, беж
tags: warm, restaurant, food, cafe, editorial, terracotta, cream, menu, hospitality, elegant, ресторан, кафе, меню, бронирован, еда, кухн
stack: html, tailwind
summary: Warm cream-and-terracotta restaurant site — editorial type, menu with price leaders, reservation.
---

# Ember — warm editorial restaurant
For restaurants, cafés, bakeries, bars. Warm, appetizing, editorial. Food photos do the
work — don't over-decorate.

## Tokens
bg `#FBF6EE` · surface `#FFF` · primary `#B4531F` · primary-hover `#963F13` · accent `#E0A458` ·
text `#2B2018` · muted `#6E5F52` · border `#EAE0D2`.
Display serif (Playfair/Fraunces) headings only; body Inter. h1 clamp(2.5rem,6vw,4.5rem).
Images/cards `rounded-lg`, buttons `rounded-full`. Soft, warm, no harsh borders.

## Layout order
nav → hero (dish photo overlay + tagline + reserve CTA) → story band → menu (dotted price
leaders) → gallery strip → hours + address → reservation CTA → footer.

## Snippets
Hero:
```html
<section class="relative">
  <img src="/dish.jpg" class="w-full h-[70vh] object-cover"/><div class="absolute inset-0 bg-black/30"></div>
  <div class="absolute inset-0 flex flex-col items-center justify-center text-center text-white px-6">
    <p class="uppercase tracking-[0.3em] text-sm text-[#E0A458]">Est. 2014 · Wood-fired</p>
    <h1 class="font-serif text-4xl md:text-6xl mt-4">Ember Kitchen</h1>
    <p class="mt-4 max-w-md text-white/90">Seasonal plates, open fire, natural wine.</p>
    <a href="#reserve" class="mt-8 px-8 py-3 rounded-full bg-[#B4531F] hover:bg-[#963F13]">Reserve a table</a>
  </div>
</section>
```
Menu (anchor block — dotted price leaders):
```html
<section class="max-w-3xl mx-auto px-6 py-24">
  <h2 class="font-serif text-3xl text-[#2B2018] text-center mb-12">The menu</h2>
  <p class="uppercase tracking-widest text-xs text-[#B4531F] mb-4">Small plates</p>
  <ul class="space-y-5"><li><!-- repeat -->
    <div class="flex items-baseline gap-3">
      <span class="text-[#2B2018] font-medium">Charred leeks, hazelnut</span>
      <span class="flex-1 border-b border-dotted border-[#EAE0D2] translate-y-[-3px]"></span>
      <span class="text-[#6E5F52]">$14</span></div>
    <p class="text-sm text-[#6E5F52] mt-1">romesco, aged sherry</p>
  </li></ul>
</section>
```
Hours + reservation:
```html
<section id="reserve" class="bg-[#B4531F] text-white"><div class="max-w-5xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
  <div><h2 class="font-serif text-3xl">Join us this week</h2>
    <p class="mt-3 text-white/80">Dinner Tue–Sun 5–11pm · 42 Kiln Street</p>
    <a class="inline-block mt-6 px-8 py-3 rounded-full bg-white text-[#B4531F] font-medium">Book on Resy</a></div>
  <dl class="text-white/90 space-y-2">
    <div class="flex justify-between border-b border-white/20 py-2"><dt>Tue–Thu</dt><dd>5–10pm</dd></div>
    <div class="flex justify-between py-2"><dt>Fri–Sat</dt><dd>5–11pm</dd></div></dl>
</div></section>
```

## Adaptation
Menu block with dotted price leaders is mandatory. Always include hours + address +
reservation CTA. Cream bg + terracotta primary. Serif for headings only; body stays sans.
