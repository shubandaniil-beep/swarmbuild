---
id: glass-hero
name: Aura — glassmorphism
domain: saas, app, tech, ai, product, crypto, startup, приложение, продукт, технологии, ии, стартап
style: glassmorphism, modern, frosted, sleek, futuristic, стекло, современ, футуризм
colors: gradient, blur, violet, cyan, glass, градиент, фиолет, циан
tags: glassmorphism, glass, frosted, blur, gradient, modern, ai, tech, translucent, cards, стекло, блюр, градиент, современ, прозрачн
stack: html, tailwind
summary: Glassmorphism — colorful gradient bg, frosted translucent cards with blur and thin borders.
---

# Aura — glassmorphism
For modern SaaS/AI/tech/crypto products wanting a sleek futuristic look. Colorful gradient
background, frosted translucent glass cards floating over it.

## Tokens
Base gradient bg `linear-gradient(135deg,#6D28D9,#2563EB,#06B6D4)` (or brand hues). Glass:
`bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl`. Text `#FFF` / `text-white/70`.
Font Inter/Geist. Soft glow, thin light borders. Add faint colored blobs behind the glass.

## Layout order
glass nav bar → hero (headline + subcopy + CTA, on gradient) → floating glass feature cards →
glass stat panel → glass pricing → CTA → footer. Everything sits on the one gradient.

## Snippets
Gradient shell + glass nav + hero:
```html
<div class="min-h-screen relative text-white" style="background:linear-gradient(135deg,#6D28D9,#2563EB,#06B6D4)">
  <div class="absolute top-40 left-10 w-72 h-72 rounded-full bg-fuchsia-400/30 blur-3xl"></div>
  <header class="relative max-w-6xl mx-auto px-6 mt-4">
    <nav class="flex items-center justify-between px-5 h-14 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20">
      <span class="font-semibold">Aura</span>
      <a class="px-4 py-1.5 rounded-lg bg-white text-[#2563EB] text-sm font-medium">Try free</a></nav>
  </header>
  <section class="relative max-w-3xl mx-auto px-6 pt-24 pb-16 text-center">
    <h1 class="text-4xl md:text-6xl font-semibold">Intelligence, beautifully clear.</h1>
    <p class="mt-5 text-white/70">The AI workspace that feels like light.</p>
    <a class="inline-block mt-8 px-6 py-3 rounded-xl bg-white/15 backdrop-blur-xl border border-white/25 hover:bg-white/25 transition">Get started</a>
  </section>
</div>
```
Glass feature card:
```html
<div class="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 p-6"><!-- repeat -->
  <div class="w-10 h-10 rounded-lg bg-white/20 grid place-items-center mb-4">✦</div>
  <h3 class="font-medium">Realtime sync</h3><p class="text-sm text-white/70 mt-2">Everything, instantly.</p></div>
```

## Adaptation
The whole page sits on ONE gradient; all panels are `bg-white/10 backdrop-blur-xl border
border-white/20`. Add 1–2 faint colored blobs behind the glass for depth. Keep text white with
`/70` muted. Don't overdo blur count — glass works because the bg is vivid. Great for AI/tech.
