---
id: playful-pastel
name: Bloom — playful pastel
domain: kids, food, snacks, app, startup, toys, family, ice cream, дети, детск, еда, снеки, игрушки, семья, мороженое
style: playful, rounded, friendly, cheerful, playful, игрив, дружелюб, весел
colors: pastel, pink, mint, yellow, пастель, розов, мятн, желт
tags: playful, pastel, kids, food, snacks, fun, rounded, cheerful, bubbly, family, игрив, детск, пастель, весел, еда, дружелюб
stack: html, tailwind
summary: Bubbly pastel site — rounded blobs, playful type, big buttons; for kids/food/fun brands.
---

# Bloom — playful pastel
For kids brands, snacks/food, fun consumer apps, toys, family products. Cheerful, rounded,
soft pastels, bouncy. Fun without looking cheap.

## Tokens
bg `#FFF7F2` · surface `#FFF` · text `#3A2B3F` · muted `#8A7A8F` · pink `#FF7EB3` ·
mint `#6FE3C4` · yellow `#FFD166` · border `#F2E3EA`. Rounded display font (Baloo/Poppins bold).
Everything `rounded-3xl` / `rounded-full`. Soft blob shapes, big playful buttons, gentle shadows.

## Layout order
chunky nav → hero (big cheerful headline + emoji/illustration + big CTA + blob bg) →
feature cards (pastel-tinted, one color each) → fun stat/marquee → testimonial bubbles →
newsletter → footer with wave.

## Snippets
Hero:
```html
<section class="relative overflow-hidden px-6 pt-16 pb-20 text-center">
  <div class="absolute -top-10 -left-10 w-64 h-64 rounded-full bg-[#6FE3C4]/40 blur-2xl"></div>
  <div class="absolute top-20 -right-10 w-72 h-72 rounded-full bg-[#FFD166]/40 blur-2xl"></div>
  <div class="relative max-w-2xl mx-auto">
    <h1 class="text-5xl md:text-6xl font-extrabold text-[#3A2B3F]">Snacks that make you <span class="text-[#FF7EB3]">smile</span> 🍓</h1>
    <p class="mt-5 text-[#8A7A8F] text-lg">Wholesome, colorful, delightfully snackable.</p>
    <a class="inline-block mt-8 px-8 py-4 rounded-full bg-[#FF7EB3] text-white font-bold text-lg shadow-lg hover:-translate-y-0.5 transition">Order a box</a>
  </div>
</section>
```
Pastel feature card:
```html
<section class="max-w-5xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
  <div class="rounded-3xl bg-[#6FE3C4]/20 p-6 text-center"><!-- vary bg color per card -->
    <div class="text-4xl mb-3">🌱</div>
    <h3 class="font-bold text-[#3A2B3F]">All natural</h3><p class="text-sm text-[#8A7A8F] mt-2">No junk, ever.</p></div>
</section>
```

## Adaptation
Rounded-everything (`rounded-3xl`/`full`), big bold friendly type, soft pastel blobs in the bg.
Rotate pastel tints per card (pink/mint/yellow). Emoji or simple illustrations are welcome.
Keep it cheerful but not cluttered. Great for kids, food, and fun DTC brands.
