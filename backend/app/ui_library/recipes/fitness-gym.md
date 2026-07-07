---
id: fitness-gym
name: Forge — fitness / gym
domain: fitness, gym, training, crossfit, coach, workout, фитнес, спортзал, тренировк, тренер, кроссфит, зал
style: bold, energetic, dark, dynamic, motivating, энергичн, ярк, дерзк, мотивир
colors: dark, lime, black, energetic, темн, лайм, ярк
tags: fitness, gym, training, crossfit, coach, workout, classes, membership, join, фитнес, спортзал, тренировк, тренер, абонемент, классы
stack: html, tailwind
summary: High-energy dark gym site — bold hero, class schedule, membership tiers, trainer cards, join CTA.
---

# Forge — fitness / gym
For gyms, fitness studios, CrossFit, personal trainers, sports. High-energy, dark, punchy,
motivating. Strong verbs, bold type, a clear join/membership path.

## Tokens
bg `#0C0E0B` · surface `#15180F` · text `#F4F7EE` · muted `#9BA491` · primary `#B6FF3C` (lime) ·
border `#242A1C`. Heavy condensed/bold font (Anton/Oswald headings, Inter body). UPPERCASE
headings, h1 clamp(2.6rem,7vw,5rem). Lime on CTAs, highlights, numbers. Sharp `rounded-lg`.

## Layout order
nav (+ Join) → hero (bold headline over action photo + join CTA) → stats band (members, classes) →
class schedule (grid/list) → membership tiers (highlight one) → trainers → CTA → footer.

## Snippets
Hero:
```html
<section class="relative"><div class="h-[75vh]"><img src="/gym.jpg" class="w-full h-full object-cover"/>
  <div class="absolute inset-0 bg-black/55"></div></div>
  <div class="absolute inset-0 flex flex-col justify-center px-6 max-w-6xl mx-auto">
    <p class="text-[#B6FF3C] font-bold tracking-widest">NO EXCUSES</p>
    <h1 class="text-5xl md:text-7xl font-extrabold uppercase text-[#F4F7EE] mt-3 leading-none">Train<br>like it counts.</h1>
    <a class="inline-block mt-8 w-fit px-8 py-3 rounded-lg bg-[#B6FF3C] text-[#0C0E0B] font-bold uppercase">Join now</a>
  </div>
</section>
```
Membership tier + class row:
```html
<div class="rounded-lg border-2 border-[#B6FF3C] bg-[#15180F] p-6"><!-- highlighted tier -->
  <p class="text-[#B6FF3C] font-bold uppercase text-sm">Unlimited</p>
  <p class="text-4xl font-extrabold text-[#F4F7EE] mt-1">$59<span class="text-base text-[#9BA491]">/mo</span></p>
  <a class="block text-center mt-6 px-4 py-2 rounded-lg bg-[#B6FF3C] text-[#0C0E0B] font-bold uppercase">Get started</a></div>
<div class="flex items-center justify-between border-b border-[#242A1C] py-4"><!-- class row -->
  <div><p class="text-[#F4F7EE] font-semibold uppercase">HIIT Blast</p><p class="text-sm text-[#9BA491]">Mon · 6:00 AM · Coach Rey</p></div>
  <span class="text-[#B6FF3C] text-sm">45 min</span></div>
```

## Adaptation
Dark base + lime energy accent (recolor accent if brand differs). UPPERCASE bold headings,
motivating copy. Class schedule + membership tiers (one highlighted) + trainers are expected.
Action photography in the hero. Keep it loud and driven — never soft or pastel.
