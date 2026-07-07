---
id: beauty-salon
name: Petal — beauty / salon / spa
domain: beauty, salon, spa, hair, nails, cosmetics, barber, wellness, красота, салон, спа, парикмахер, ногти, косметика, барбершоп
style: elegant, soft, feminine, calm, refined, элегант, нежн, спокойн
colors: blush, nude, rose-gold, cream, розов, беж, нюд
tags: beauty, salon, spa, hair, nails, cosmetics, barber, services, booking, price list, красота, салон, спа, услуги, запись, прайс
stack: html, tailwind
summary: Soft blush salon/spa site — services price list, booking CTA, gallery, elegant serif.
---

# Petal — beauty / salon / spa
For beauty salons, spas, hair/nail studios, cosmetics, wellness (barbershops → swap to darker
palette). Soft, elegant, calm; a clear services-with-prices list and booking.

## Tokens
bg `#FBF4F1` · surface `#FFF` · text `#3B2A2E` · muted `#8A6E72` · primary `#C08497` (blush-rose) ·
accent `#D7B98E` (rose-gold) · border `#EFE0DB`. Display serif (Cormorant/Playfair); body Inter.
h1 clamp(2.2rem,5vw,3.5rem). Soft `rounded-2xl`, gentle shadows, airy.

## Layout order
nav (+ "Book") → hero (elegant headline + book CTA + photo) → services price list →
gallery strip → about/team → testimonials → hours + booking → footer.

## Snippets
Hero:
```html
<section class="max-w-6xl mx-auto px-6 pt-16 pb-12 grid md:grid-cols-2 gap-10 items-center">
  <div><p class="uppercase tracking-[0.25em] text-xs text-[#D7B98E]">Studio & Spa</p>
    <h1 class="font-serif text-4xl md:text-5xl text-[#3B2A2E] mt-3">Where you slow down and glow.</h1>
    <p class="mt-4 text-[#8A6E72] max-w-md">Hair, skin and nail care by hands that care.</p>
    <a class="inline-block mt-8 px-7 py-3 rounded-full bg-[#C08497] text-white">Book now</a></div>
  <div class="aspect-[4/5] bg-[#EFE0DB] rounded-2xl"></div>
</section>
```
Services price list (the anchor):
```html
<section class="max-w-3xl mx-auto px-6 py-20">
  <h2 class="font-serif text-3xl text-[#3B2A2E] text-center mb-10">Services</h2>
  <ul class="space-y-4"><li><!-- repeat -->
    <div class="flex items-baseline gap-3">
      <span class="text-[#3B2A2E] font-medium">Signature facial</span>
      <span class="flex-1 border-b border-dotted border-[#EFE0DB] translate-y-[-3px]"></span>
      <span class="text-[#8A6E72]">$85 · 60 min</span></div></li></ul>
</section>
```

## Adaptation
Services list with prices + duration and dotted leaders is the core (people come to book a
specific service). Book CTA in nav, hero, and a closing section. Soft blush/rose-gold palette,
elegant serif headings. For a men's barbershop, keep the structure but shift to charcoal + amber.
