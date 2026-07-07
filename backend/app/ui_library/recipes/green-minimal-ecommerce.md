---
id: green-minimal-ecommerce
name: Verdant — minimal green storefront
domain: ecommerce, clothing, retail, shop, магазин, одежд, продаж, товар, каталог
style: minimal, clean, airy, modern, минимал, чист
colors: green, sage, monochrome, зелен
tags: green, minimal, ecommerce, clothing, store, shop, sage, whitespace, grid, catalog, магазин, одежд, зелен, минимал, корзин, товар
stack: html, tailwind
summary: Airy sage-green storefront for fashion/retail. Whitespace, product grid, slim sticky nav.
---

# Verdant — minimal green storefront
For clean calm shops: clothing, cosmetics, plants, lifestyle. Keep the restraint —
no gradients, no heavy shadows, no carousels.

## Tokens
bg `#F7F8F5` · surface `#FFF` · primary `#3F6B4C` · primary-hover `#345A40` ·
accent `#8FB39B` · text `#1C2A21` · muted `#5C6B60` · border `#E3E7E0`.
Fonts: headings serif (Fraunces/Playfair), body Inter. h1 clamp(2.2rem,5vw,3.75rem).
Container `max-w-6xl mx-auto px-6`. Sections `py-20 md:py-28`. Images `rounded-none`,
buttons `rounded-full`. Borders over shadows. Max 2 fonts.

## Layout order
slim sticky nav → hero (1 photo + 1 line) → product grid (4 col, 4:5) →
editorial band → newsletter strip → minimal footer.

## Snippets
Nav:
```html
<header class="sticky top-0 z-40 bg-[#F7F8F5]/80 backdrop-blur border-b border-[#E3E7E0]">
  <nav class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
    <a class="font-serif text-xl text-[#1C2A21]">Verdant</a>
    <ul class="hidden md:flex gap-8 text-sm text-[#5C6B60]">
      <li><a class="hover:text-[#3F6B4C]">Shop</a></li><li><a class="hover:text-[#3F6B4C]">About</a></li>
    </ul>
    <a class="text-sm px-4 py-2 rounded-full bg-[#3F6B4C] text-white hover:bg-[#345A40]">Cart (0)</a>
  </nav>
</header>
```
Hero:
```html
<section class="max-w-6xl mx-auto px-6 pt-16 pb-24 grid md:grid-cols-2 gap-10 items-center">
  <div>
    <p class="text-sm uppercase tracking-[0.2em] text-[#8FB39B] mb-4">Spring collection</p>
    <h1 class="font-serif text-[#1C2A21] text-4xl md:text-6xl leading-tight">Clothes that breathe.</h1>
    <p class="mt-6 text-[#5C6B60] max-w-md">Naturally dyed, small batches.</p>
    <a class="inline-block mt-8 px-7 py-3 rounded-full bg-[#3F6B4C] text-white hover:bg-[#345A40]">Shop</a>
  </div>
  <div class="aspect-[4/5] bg-[#E3E7E0]"><img src="/hero.jpg" class="w-full h-full object-cover"/></div>
</section>
```
Product grid (core):
```html
<section id="shop" class="max-w-6xl mx-auto px-6 py-20">
  <div class="flex items-end justify-between mb-10">
    <h2 class="font-serif text-3xl text-[#1C2A21]">New in</h2>
    <a class="text-sm text-[#3F6B4C] hover:underline">View all</a>
  </div>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-10">
    <article class="group"><!-- repeat -->
      <div class="aspect-[4/5] bg-[#EDF0EA] overflow-hidden mb-3">
        <img src="/p1.jpg" class="w-full h-full object-cover group-hover:scale-105 transition duration-500"/></div>
      <h3 class="text-sm text-[#1C2A21]">Linen shirt</h3><p class="text-sm text-[#5C6B60]">$68</p>
    </article>
  </div>
</section>
```

## Adaptation
Swap catalog, keep 4-col 4:5 grid. Recolor only the `#3F6B4C`/`#8FB39B` pair if client
names a color. Never add a carousel or a 3rd font. Newsletter strip uses `bg-[#3F6B4C]`.
