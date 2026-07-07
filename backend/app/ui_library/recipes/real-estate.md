---
id: real-estate
name: Terra — real estate / property
domain: real estate, property, realtor, housing, rent, apartments, недвижимость, аренда, квартиры, жилье, риелтор, дома
style: clean, trustworthy, modern, photographic, чист, современ
colors: green-neutral, teal, warm-white, зелен, нейтрал
tags: real estate, property, realtor, housing, rent, apartments, listings, search, map, agent, недвижимость, аренда, квартиры, жилье, поиск, объявления
stack: html, tailwind
summary: Property site — search hero, listing cards with price/beds/area, agent CTA, map.
---

# Terra — real estate / property
For real estate agencies, rentals, property listings. Search-first, photo-forward, trust
signals. Listings are the product.

## Tokens
bg `#FCFCFB` · surface `#FFF` · text `#16241E` · muted `#5F7169` · primary `#127A63` (teal-green) ·
accent `#E8B04B` · border `#E6EBE8`. Font Inter. Cards `rounded-2xl border shadow-sm`.
h1 clamp(2rem,4vw,3rem). Price prominent, `tabular-nums`.

## Layout order
nav → hero with search bar (location / type / price) → featured listings (3-col cards) →
"why us" trust row (stats) → agent/contact band → map placeholder → footer.

## Snippets
Hero + search:
```html
<section class="relative"><div class="h-[60vh] bg-[#E6EBE8]"><img src="/city.jpg" class="w-full h-full object-cover"/></div>
  <div class="absolute inset-0 bg-black/25 flex items-center justify-center px-6">
    <div class="w-full max-w-3xl text-center text-white">
      <h1 class="text-3xl md:text-5xl font-semibold">Find a place to love.</h1>
      <form class="mt-8 bg-white rounded-2xl p-2 flex flex-col md:flex-row gap-2 text-[#16241E]">
        <input placeholder="City or ZIP" class="flex-1 px-4 py-3 rounded-xl"/>
        <select class="px-4 py-3 rounded-xl"><option>Buy</option><option>Rent</option></select>
        <button class="px-6 py-3 rounded-xl bg-[#127A63] text-white">Search</button>
      </form></div></div>
</section>
```
Listing card:
```html
<article class="rounded-2xl border border-[#E6EBE8] bg-white shadow-sm overflow-hidden"><!-- repeat -->
  <div class="aspect-[4/3] bg-[#E6EBE8] relative"><img src="/h1.jpg" class="w-full h-full object-cover"/>
    <span class="absolute top-3 left-3 bg-[#E8B04B] text-[#16241E] text-xs px-2 py-1 rounded-full">New</span></div>
  <div class="p-4">
    <p class="text-lg font-semibold tabular-nums">$420,000</p>
    <p class="text-sm text-[#5F7169]">3 bd · 2 ba · 1,450 sqft</p>
    <p class="text-sm text-[#16241E] mt-1">142 Maple Ave, Portland</p></div>
</article>
```

## Adaptation
Search bar in the hero is mandatory (location + type + price). Listing card = photo + price
(big, tabular) + beds/baths/area + address, optional status pill. Include a trust/stats row
and an agent contact path. Photo quality carries the page.
