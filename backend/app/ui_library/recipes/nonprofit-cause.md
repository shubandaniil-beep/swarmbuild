---
id: nonprofit-cause
name: Grove — nonprofit / cause
domain: nonprofit, charity, ngo, foundation, cause, donation, volunteer, church, некоммерч, благотворитель, фонд, пожертвование, волонтер
style: warm, hopeful, human, trustworthy, тепл, человечн, доверие
colors: green, warm, earthy, зелен, тепл, земл
tags: nonprofit, charity, ngo, foundation, cause, donation, volunteer, impact, mission, donate, некоммерч, благотворитель, фонд, пожертвование, волонтер, миссия
stack: html, tailwind
summary: Warm nonprofit site — mission hero, impact numbers, donate CTA, ways to help, stories.
---

# Grove — nonprofit / cause
For nonprofits, charities, NGOs, foundations, community causes. Warm, human, hopeful,
trustworthy. Two clear actions: donate and get involved. Impact numbers build trust.

## Tokens
bg `#FBF9F3` · surface `#FFF` · text `#22301F` · muted `#5E6B58` · primary `#2E7D46` (green) ·
accent `#E0A32E` (warm gold) · border `#E6E9DF`. Font Inter; headings can be a warm serif.
Cards `rounded-2xl border`. Human photography. Donate button prominent everywhere.

## Layout order
nav (+ prominent Donate) → hero (mission line + donate CTA + human photo) → impact stats band →
the problem / mission → ways to help (donate / volunteer / share cards) → story/testimonial →
donation tiers → footer.

## Snippets
Hero + impact:
```html
<section class="max-w-6xl mx-auto px-6 pt-16 pb-12 grid md:grid-cols-2 gap-10 items-center">
  <div><p class="text-sm font-medium text-[#E0A32E]">Clean water for all</p>
    <h1 class="text-4xl md:text-5xl font-semibold text-[#22301F] mt-3">Every gift becomes a well.</h1>
    <p class="mt-4 text-[#5E6B58] max-w-md">We bring safe water to villages that need it most.</p>
    <div class="mt-8 flex gap-3"><a class="px-6 py-3 rounded-xl bg-[#2E7D46] text-white font-medium">Donate</a>
      <a class="px-6 py-3 rounded-xl border border-[#E6E9DF] text-[#22301F]">Volunteer</a></div></div>
  <div class="aspect-[4/3] bg-[#E6E9DF] rounded-2xl"></div>
</section>
<section class="bg-[#2E7D46] text-white"><div class="max-w-6xl mx-auto px-6 py-10 grid grid-cols-3 gap-4 text-center">
  <div><p class="text-3xl font-semibold">240+</p><p class="text-sm text-white/80">wells built</p></div>
  <div><p class="text-3xl font-semibold">90k</p><p class="text-sm text-white/80">people served</p></div>
  <div><p class="text-3xl font-semibold">92%</p><p class="text-sm text-white/80">to programs</p></div>
</div></section>
```
Ways-to-help / donation tier:
```html
<div class="rounded-2xl border border-[#E6E9DF] bg-white p-6 text-center"><!-- tier, repeat -->
  <p class="text-3xl font-semibold text-[#2E7D46]">$50</p>
  <p class="text-sm text-[#5E6B58] mt-2">Clean water for a family for a year</p>
  <a class="block mt-5 px-4 py-2 rounded-lg bg-[#2E7D46] text-white">Give $50</a></div>
```

## Adaptation
Donate button appears in nav + hero + a tiers section. Impact numbers band (built / served / %
to cause) is essential for trust. Tie donation amounts to concrete outcomes ("$50 = a year of
water"). Warm green + gold, human photography. Hopeful, never guilt-heavy.
