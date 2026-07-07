---
id: marketplace
name: Bazaar — marketplace / multi-vendor
domain: marketplace, multi-vendor, listings, classifieds, services platform, gig, rental platform, маркетплейс, объявления, площадка, услуги, аренда, доска
style: functional, trustworthy, dense, modern, функционал, чист
colors: neutral, blue, white, нейтрал, син
tags: marketplace, multi-vendor, listings, classifieds, services, gig, rental, search, filters, categories, ratings, маркетплейс, объявления, площадка, поиск, фильтры, категории, рейтинг
stack: html, tailwind
summary: Marketplace — search + category chips, filter sidebar, listing grid with seller/rating/price.
---

# Bazaar — marketplace / multi-vendor
For marketplaces, classifieds, services/gig platforms, rental platforms. Search + filter +
listings is the whole product. Trust signals (ratings, verified) matter.

## Tokens
bg `#F7F8FA` · surface `#FFF` · text `#141A1F` · muted `#667085` · primary `#2563EB` ·
accent `#F59E0B` (rating stars) · border `#E5E8EC`. Font Inter, 14–15px. Cards `rounded-xl border`.
Prices bold `tabular-nums`. Category chips `rounded-full`.

## Layout order
nav (search bar + sell CTA) → category chips row → [filter sidebar | listing grid] →
pagination → trust band → footer.

## Snippets
Search nav + category chips:
```html
<header class="bg-white border-b"><div class="max-w-7xl mx-auto px-6 h-16 flex items-center gap-4">
  <a class="font-bold text-[#2563EB]">Bazaar</a>
  <div class="flex-1 max-w-xl flex"><input placeholder="Search listings" class="flex-1 px-4 py-2 rounded-l-lg border border-r-0"/>
    <button class="px-5 rounded-r-lg bg-[#2563EB] text-white">Search</button></div>
  <a class="ml-auto px-4 py-2 rounded-lg bg-[#141A1F] text-white text-sm">+ Sell</a>
</div></header>
<div class="max-w-7xl mx-auto px-6 py-4 flex gap-2 overflow-x-auto">
  <button class="px-4 py-1.5 rounded-full bg-[#2563EB] text-white text-sm">All</button>
  <button class="px-4 py-1.5 rounded-full border text-sm">Electronics</button>
  <button class="px-4 py-1.5 rounded-full border text-sm">Home</button>
</div>
```
Sidebar + listing card:
```html
<div class="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-6">
  <aside class="hidden lg:block bg-white rounded-xl border p-4 text-sm space-y-4">
    <div><p class="font-medium mb-2">Price</p><div class="flex gap-2"><input class="w-full border rounded px-2 py-1" placeholder="min"/><input class="w-full border rounded px-2 py-1" placeholder="max"/></div></div>
    <div><p class="font-medium mb-2">Rating</p><label class="flex gap-2 items-center"><input type="checkbox"/> 4★ & up</label></div>
  </aside>
  <div class="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
    <article class="bg-white rounded-xl border overflow-hidden"><!-- repeat -->
      <div class="aspect-square bg-[#E5E8EC]"></div>
      <div class="p-3"><p class="font-semibold tabular-nums">$240</p>
        <p class="text-sm text-[#141A1F] truncate">Vintage desk lamp</p>
        <p class="text-xs text-[#667085] mt-1"><span class="text-[#F59E0B]">★ 4.7</span> · Seller_88</p></div></article>
  </div>
</div>
```

## Adaptation
Search bar + category chips + filter sidebar + listing grid are the skeleton. Each card shows
photo + price (bold) + title + seller + rating. Add a "Sell" CTA. Keep it dense and functional,
neutral base with a blue primary and amber stars.
