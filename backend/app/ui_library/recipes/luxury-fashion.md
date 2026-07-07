---
id: luxury-fashion
name: Noir — luxury fashion / brand
domain: luxury, fashion, jewelry, watches, beauty, brand, boutique, люкс, мода, ювелир, часы, бренд, бутик
style: luxury, elegant, dramatic, editorial, minimal, люкс, элегант, премиум
colors: black, gold, monochrome, dark, черн, золот
tags: luxury, fashion, jewelry, watches, beauty, brand, boutique, elegant, gold, black, editorial, люкс, мода, премиум, ювелир, бренд, золот
stack: html, tailwind
summary: Black-and-gold luxury brand site — full-bleed imagery, sparse type, refined restraint.
---

# Noir — luxury fashion / brand
For luxury fashion, jewelry, watches, high-end beauty, premium brands. Restraint = luxury:
huge imagery, sparse elegant type, generous space, slow reveals.

## Tokens
bg `#0A0A0A` · surface `#141414` · text `#F2EFE9` · muted `#9C978C` · gold `#C6A662` ·
border `#2A2724`. Display serif (Cormorant/Didot) thin weights; body sans letter-spaced.
h1 clamp(2.5rem,6vw,5rem) tracking-tight. Buttons: thin gold border, no fill. Radius none.
Uppercase micro-labels `tracking-[0.3em] text-xs`.

## Layout order
transparent nav (centered wordmark) → full-bleed hero image + one line + thin CTA →
2-up editorial split → product/collection row (large, few items) → brand story → footer.

## Snippets
Nav + hero:
```html
<header class="absolute top-0 inset-x-0 z-30"><nav class="max-w-6xl mx-auto px-6 h-20 flex items-center justify-between text-[#F2EFE9]">
  <a class="text-xs tracking-[0.3em]">MENU</a><a class="font-serif text-2xl tracking-wide">NOIR</a><a class="text-xs tracking-[0.3em]">BAG</a>
</nav></header>
<section class="relative h-screen"><img src="/hero.jpg" class="w-full h-full object-cover"/>
  <div class="absolute inset-0 bg-black/25"></div>
  <div class="absolute inset-0 flex flex-col items-center justify-center text-center text-[#F2EFE9]">
    <p class="text-xs tracking-[0.3em] text-[#C6A662]">THE WINTER EDIT</p>
    <h1 class="font-serif text-5xl md:text-7xl mt-4 font-light">Timeless by design.</h1>
    <a class="mt-8 px-8 py-3 border border-[#C6A662] text-xs tracking-[0.3em] hover:bg-[#C6A662] hover:text-black transition">DISCOVER</a>
  </div>
</section>
```
Collection row:
```html
<section class="max-w-6xl mx-auto px-6 py-24 grid md:grid-cols-3 gap-8">
  <article class="text-center"><!-- repeat, keep FEW items -->
    <div class="aspect-[3/4] bg-[#141414] mb-4"><img src="/p1.jpg" class="w-full h-full object-cover"/></div>
    <p class="text-xs tracking-[0.3em] text-[#9C978C]">FINE JEWELRY</p>
    <h3 class="font-serif text-xl mt-1">Aurelia Ring</h3></article>
</section>
```

## Adaptation
Never crowd — few products, big images, lots of black space. Gold is an accent only (labels,
thin borders, hover), never a fill-everything. Thin serif display, uppercase spaced micro-labels.
Outlined buttons, no rounded corners. Slow, quiet, expensive.
