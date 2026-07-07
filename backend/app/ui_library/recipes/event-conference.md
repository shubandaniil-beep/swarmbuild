---
id: event-conference
name: Summit — event / conference
domain: event, conference, meetup, festival, webinar, workshop, summit, событ, конференц, фестивал, вебинар, митап
style: bold, energetic, modern, gradient, ярк, энергичн
colors: gradient, purple, orange, vibrant, градиент, фиолет, оранжев
tags: event, conference, meetup, festival, webinar, workshop, summit, speakers, schedule, tickets, register, событ, конференц, спикер, расписан, билет, регистрац
stack: html, tailwind
summary: Conference landing — date/location hero, speakers grid, schedule, ticket tiers, register CTA.
---

# Summit — event / conference
For conferences, meetups, festivals, webinars, workshops. Energetic, time-bound, urgency
(date/countdown), clear register CTA.

## Tokens
bg `#0E0B1A` · surface `#191330` · text `#F3F0FF` · muted `#A79FC7` · gradient
`linear-gradient(120deg,#7C3AED,#F97316)` · border `#2A2246`. Font Space Grotesk/Inter, bold.
Big date. Cards `rounded-2xl border`. Gradient on headline word, CTAs, ticket highlight.

## Layout order
nav (+ Register) → hero (event name, date + city, register CTA, countdown) → speakers grid →
schedule (day tabs / agenda list) → ticket tiers (early-bird highlighted) → venue → CTA → footer.

## Snippets
Hero:
```html
<section class="relative overflow-hidden text-center px-6 pt-24 pb-16">
  <div class="absolute inset-0 opacity-25 blur-3xl" style="background:radial-gradient(600px 300px at 50% 0%,#7C3AED,transparent)"></div>
  <div class="relative max-w-3xl mx-auto">
    <p class="text-sm tracking-widest text-[#A79FC7]">JUN 12–14 · BERLIN</p>
    <h1 class="text-5xl md:text-7xl font-bold text-[#F3F0FF] mt-4">The <span class="text-transparent bg-clip-text" style="background-image:linear-gradient(120deg,#7C3AED,#F97316)">Future</span> Summit</h1>
    <p class="mt-5 text-[#A79FC7]">3 days · 40 speakers · 2,000 builders.</p>
    <a class="inline-block mt-8 px-8 py-3 rounded-xl text-white font-semibold" style="background:linear-gradient(120deg,#7C3AED,#F97316)">Get tickets</a>
  </div>
</section>
```
Speaker card + ticket tier:
```html
<article class="rounded-2xl border border-[#2A2246] bg-[#191330] overflow-hidden"><!-- speaker -->
  <div class="aspect-square bg-[#2A2246]"></div>
  <div class="p-4"><h3 class="text-[#F3F0FF] font-medium">Maya Okonkwo</h3><p class="text-sm text-[#A79FC7]">CTO, Northwind</p></div></article>
<div class="rounded-2xl p-6" style="background:linear-gradient(120deg,#7C3AED,#F97316)"><!-- highlighted tier -->
  <p class="text-white/80 text-sm">Early bird</p><p class="text-4xl font-bold text-white mt-1">$149</p>
  <a class="block text-center mt-6 px-4 py-2 rounded-lg bg-white text-[#7C3AED] font-semibold">Buy now</a></div>
```

## Adaptation
Date + city + register CTA must be in the hero (add a countdown if event is upcoming). Speakers
grid, schedule, and ticket tiers (early-bird = highlighted gradient) are the backbone. Gradient
is the energy — one gradient, used on headline word + CTAs + featured tier only.
