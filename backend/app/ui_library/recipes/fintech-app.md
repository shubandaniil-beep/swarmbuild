---
id: fintech-app
name: Ledger — fintech / banking
domain: fintech, banking, finance, payments, wallet, crypto, invest, финтех, банк, финансы, платежи, кошелек, инвест
style: modern, clean, confident, secure, современ, надежн
colors: dark-teal, mint, black, neon-green, темн, мятн
tags: fintech, banking, finance, payments, wallet, crypto, invest, card, secure, app, финтех, банк, финансы, платежи, карта, инвестиции
stack: html, tailwind
summary: Fintech landing — bold headline, card/app mockup, trust + numbers, feature grid, security.
---

# Ledger — fintech / banking
For fintech, neobanks, payments, wallets, investing apps. Confident, secure, numbers-forward.
Show the product (card/app) and hard trust signals.

## Tokens
bg `#0C1613` (deep teal-black) · surface `#122019` · text `#EAF3EE` · muted `#8FA79B` ·
primary `#37E29B` (mint) · accent `#0FB37A` · border `#1E2E27`. Font Inter/Geist, tight.
Big numbers `tabular-nums`. Cards `rounded-2xl border`. Mint used sparingly on CTAs/figures.

## Layout order
nav → hero (headline + subcopy + CTA + app/card mockup) → trust bar (regulated, $ moved, users) →
feature grid (send, invest, track) → security section (badges) → pricing/plans → CTA → footer.

## Snippets
Hero:
```html
<section class="max-w-6xl mx-auto px-6 pt-20 pb-16 grid md:grid-cols-2 gap-10 items-center">
  <div><span class="text-xs px-3 py-1 rounded-full border border-[#1E2E27] text-[#8FA79B]">FCA-regulated</span>
    <h1 class="text-4xl md:text-6xl font-semibold text-[#EAF3EE] mt-5 tracking-tight">Money that moves at your speed.</h1>
    <p class="mt-5 text-[#8FA79B] max-w-md">Send, spend and invest from one account. No hidden fees.</p>
    <a class="inline-block mt-8 px-6 py-3 rounded-xl bg-[#37E29B] text-[#0C1613] font-semibold">Open account</a></div>
  <div class="aspect-[3/4] rounded-2xl bg-gradient-to-b from-[#122019] to-[#0C1613] border border-[#1E2E27]"></div>
</section>
```
Trust numbers + feature card:
```html
<section class="border-y border-[#1E2E27]"><div class="max-w-6xl mx-auto px-6 py-8 grid grid-cols-3 gap-4 text-center">
  <div><p class="text-3xl font-semibold text-[#EAF3EE] tabular-nums">$4.2B</p><p class="text-xs text-[#8FA79B]">moved / yr</p></div>
  <div><p class="text-3xl font-semibold text-[#EAF3EE] tabular-nums">1.8M</p><p class="text-xs text-[#8FA79B]">users</p></div>
  <div><p class="text-3xl font-semibold text-[#EAF3EE] tabular-nums">4.9★</p><p class="text-xs text-[#8FA79B]">App Store</p></div>
</div></section>
<div class="rounded-2xl border border-[#1E2E27] bg-[#122019] p-6"><!-- repeat -->
  <div class="w-10 h-10 rounded-lg bg-[#37E29B]/15 text-[#37E29B] grid place-items-center mb-4">↗</div>
  <h3 class="text-[#EAF3EE] font-medium">Instant transfers</h3><p class="text-sm text-[#8FA79B] mt-2">Free, 24/7, worldwide.</p></div>
```

## Adaptation
Trust numbers row + a visible product mockup (card or phone) are mandatory — fintech sells on
credibility. Mint accent only on CTAs and key figures; keep the base dark and calm. Include a
security/compliance section. Never make it look playful.
