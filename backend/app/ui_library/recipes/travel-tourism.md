---
id: travel-tourism
name: Voyage — travel / tourism
domain: travel, tourism, hotel, booking, trip, tours, vacation, resort, airline, путешествия, туризм, отель, тур, отдых, бронирование, авиа
style: airy, inspiring, photographic, clean, вдохновл, воздушн, чист
colors: sky-blue, teal, sand, warm-white, голуб, бирюз, песочн
tags: travel, tourism, hotel, booking, trip, tours, vacation, resort, destinations, search, путешествия, туризм, отель, тур, отдых, направления, бронирование
stack: html, tailwind
summary: Inspiring travel site — search hero over landscape, destination cards, tour packages, booking.
---

# Voyage — travel / tourism
For travel agencies, hotels, tour operators, destinations, booking sites. Aspirational,
photo-driven, search-first. Big imagery sells the trip.

## Tokens
bg `#FBFCFE` · surface `#FFF` · text `#0F2231` · muted `#5A7183` · primary `#0EA5C4` (sky-teal) ·
accent `#F0A24E` (sand) · border `#E4EDF2`. Font Inter; airy. Cards `rounded-2xl shadow-sm`.
h1 clamp(2.2rem,5vw,3.75rem). Prices `tabular-nums`.

## Layout order
nav → hero (search: destination/dates/guests over a landscape photo) → popular destinations
(image cards) → featured tours (price + duration + rating) → why-us → testimonials → CTA → footer.

## Snippets
Hero + search:
```html
<section class="relative"><div class="h-[68vh]"><img src="/beach.jpg" class="w-full h-full object-cover"/>
  <div class="absolute inset-0 bg-black/25"></div></div>
  <div class="absolute inset-0 flex flex-col items-center justify-center text-center text-white px-6">
    <h1 class="text-4xl md:text-6xl font-semibold">Find your next escape.</h1>
    <form class="mt-8 bg-white rounded-2xl p-2 flex flex-col md:flex-row gap-2 text-[#0F2231] w-full max-w-3xl">
      <input placeholder="Where to?" class="flex-1 px-4 py-3 rounded-xl"/>
      <input type="date" class="px-4 py-3 rounded-xl"/>
      <button class="px-6 py-3 rounded-xl bg-[#0EA5C4] text-white">Search</button>
    </form></div>
</section>
```
Destination / tour card:
```html
<article class="rounded-2xl overflow-hidden shadow-sm bg-white"><!-- repeat -->
  <div class="aspect-[4/3] bg-[#E4EDF2] relative"><img src="/d1.jpg" class="w-full h-full object-cover"/>
    <span class="absolute bottom-3 left-3 text-white font-semibold text-lg drop-shadow">Santorini</span></div>
  <div class="p-4 flex items-center justify-between">
    <div><p class="text-sm text-[#5A7183]">7 days · ★ 4.8</p></div>
    <p class="font-semibold tabular-nums">$1,240</p></div>
</article>
```

## Adaptation
Search bar (destination + dates) in the hero is mandatory. Destination cards use full-bleed
photos with an overlaid name; tour cards show duration + rating + price. Sky/teal + sand accent.
Photography is the whole mood — keep chrome light and airy.
