---
id: medical-clinic
name: Pulse — medical / clinic
domain: medical, clinic, health, doctor, dental, hospital, wellness, медицина, клиника, здоровье, врач, стоматолог, больница
style: clean, calm, trustworthy, accessible, чист, спокойн, доверие
colors: blue, teal, white, син, голуб, бел
tags: medical, clinic, health, doctor, dental, hospital, wellness, appointment, services, booking, медицина, клиника, здоровье, врач, запись, услуги
stack: html, tailwind
summary: Calm blue clinic site — appointment CTA, services, doctors, trust, booking form.
---

# Pulse — medical / clinic
For clinics, doctors, dental, wellness, hospitals. Calm, clean, reassuring, accessible.
Booking is the primary action.

## Tokens
bg `#F7FBFC` · surface `#FFF` · text `#132430` · muted `#5B7180` · primary `#1C8AC7` (calm blue) ·
accent `#28B7A6` (teal) · border `#E1EEF2`. Font Inter, generous line-height, ≥16px body.
Cards `rounded-2xl border shadow-sm`. Rounded, soft, high accessibility/contrast.

## Layout order
nav (+ phone + "Book") → hero (reassuring headline + book CTA + photo) → services (icon grid) →
doctors (photo cards) → trust (years, patients, rating) → appointment form → hours/location → footer.

## Snippets
Hero:
```html
<section class="max-w-6xl mx-auto px-6 pt-16 pb-12 grid md:grid-cols-2 gap-10 items-center">
  <div><p class="text-sm font-medium text-[#28B7A6]">Trusted family care</p>
    <h1 class="text-4xl md:text-5xl font-semibold text-[#132430] mt-3">Health care that listens.</h1>
    <p class="mt-4 text-[#5B7180] max-w-md">Same-day appointments with caring specialists.</p>
    <div class="mt-8 flex gap-3"><a class="px-6 py-3 rounded-xl bg-[#1C8AC7] text-white">Book appointment</a>
      <a class="px-6 py-3 rounded-xl border border-[#E1EEF2] text-[#132430]">Call us</a></div></div>
  <div class="aspect-[4/3] bg-[#E1EEF2] rounded-2xl"></div>
</section>
```
Service card + doctor card:
```html
<div class="rounded-2xl border border-[#E1EEF2] bg-white shadow-sm p-6"><!-- service, repeat -->
  <div class="w-11 h-11 rounded-xl bg-[#E7F5F9] text-[#1C8AC7] grid place-items-center mb-4">✚</div>
  <h3 class="font-semibold text-[#132430]">Cardiology</h3><p class="text-sm text-[#5B7180] mt-2">Heart health & screening.</p></div>
<article class="rounded-2xl border border-[#E1EEF2] bg-white shadow-sm overflow-hidden"><!-- doctor, repeat -->
  <div class="aspect-square bg-[#E1EEF2]"></div>
  <div class="p-4"><h3 class="font-semibold text-[#132430]">Dr. Lena Ford</h3><p class="text-sm text-[#5B7180]">Pediatrics</p></div></article>
```

## Adaptation
A booking CTA must appear in the nav AND hero AND its own section. Include services grid,
doctor cards, trust stats, hours + address. Keep contrast high and text ≥16px (accessibility
matters here). Soft blue/teal, rounded, calm — never dark or edgy.
