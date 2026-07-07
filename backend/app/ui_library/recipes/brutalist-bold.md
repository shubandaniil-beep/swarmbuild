---
id: brutalist-bold
name: Concrete — neo-brutalist
domain: portfolio, agency, product, startup, creative, music, event, портфолио, агентство, продукт, креатив, музыка
style: brutalist, bold, raw, experimental, high-contrast, брутализм, дерзк, смел, экспериментал
colors: high-contrast, black, white, electric, черн, бел, ярк
tags: brutalist, bold, raw, experimental, neobrutalism, borders, offset shadow, sharp, brutal, брутализм, смел, дерзк, контраст, границы
stack: html, tailwind
summary: Neo-brutalist — thick black borders, hard offset shadows, electric accent, big loud type.
---

# Concrete — neo-brutalist
For bold creative brands, indie products, music/events, agencies wanting to stand out. Loud,
raw, high-contrast, unapologetic. Use when the brief says "bold / edgy / different".

## Tokens
bg `#FFFDF5` · text `#111` · accent `#FF5C00` (electric orange) OR `#3B5BFF`. Everything has a
thick `border-2 border-black` and a hard offset shadow `shadow-[4px_4px_0_#111]`. Radius `rounded-none`
(or `rounded-md` max). Heavy grotesk (Archivo/Space Grotesk), UPPERCASE headings, big weights.

## Layout order
loud nav (bordered) → hero (giant headline + blocky CTA + sticker badge) → feature blocks
(bordered cards, offset shadows, alternating accent fills) → bold stat band → CTA → footer.

## Snippets
Nav + hero:
```html
<header class="border-b-2 border-black"><nav class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
  <span class="font-extrabold text-xl">CONCRETE■</span>
  <a class="px-4 py-2 border-2 border-black bg-[#FF5C00] font-bold shadow-[3px_3px_0_#111]">GET IT</a>
</nav></header>
<section class="max-w-5xl mx-auto px-6 py-20">
  <span class="inline-block px-3 py-1 border-2 border-black bg-[#3B5BFF] text-white font-bold rotate-[-2deg]">NEW DROP</span>
  <h1 class="text-6xl md:text-8xl font-extrabold uppercase leading-[0.95] mt-6">Design<br>that <span class="bg-[#FF5C00] px-2">shouts</span>.</h1>
  <a class="inline-block mt-8 px-6 py-3 border-2 border-black bg-white font-bold shadow-[5px_5px_0_#111] hover:shadow-[2px_2px_0_#111] hover:translate-x-0.5 transition">Start now →</a>
</section>
```
Bordered feature card:
```html
<section class="max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-6">
  <div class="border-2 border-black bg-white p-6 shadow-[5px_5px_0_#111]"><!-- alternate bg accent -->
    <div class="text-3xl">⚡</div>
    <h3 class="font-extrabold text-xl uppercase mt-3">Fast</h3><p class="mt-2">No fluff. Just ship.</p></div>
</section>
```

## Adaptation
Every card/button: `border-2 border-black` + hard offset shadow. UPPERCASE bold headings, one
electric accent (orange or blue) used as fills/highlights. Slight rotations on badges add
attitude. No soft gradients, no blur, no gentle shadows — keep it raw and loud.
