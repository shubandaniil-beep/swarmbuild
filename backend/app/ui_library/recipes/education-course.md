---
id: education-course
name: Campus — education / online course
domain: education, course, school, learning, university, academy, tutor, образование, курс, школа, обучение, университет, академия
style: friendly, clear, motivating, modern, дружелюб, ясн
colors: indigo, warm-accent, light, индиго, фиолет, светл
tags: education, course, school, learning, university, academy, tutor, lessons, enroll, curriculum, образование, курс, обучение, школа, запись, программа
stack: html, tailwind
summary: Online course/school site — hero with enroll CTA, curriculum, instructor, outcomes, pricing.
---

# Campus — education / online course
For online courses, schools, bootcamps, tutors, universities. Friendly, motivating, clear
outcomes. Enrollment is the goal.

## Tokens
bg `#FBFBFE` · surface `#FFF` · text `#1B1B2E` · muted `#63637A` · primary `#4F46E5` (indigo) ·
accent `#F59E0B` · border `#E7E7F0`. Font Inter; friendly rounded. Cards `rounded-2xl border`.
h1 clamp(2.2rem,5vw,3.5rem). Progress/checkmarks in accent.

## Layout order
nav → hero (outcome headline + enroll CTA + stats: students/rating/hours) → what you'll learn
(curriculum list w/ checks) → instructor card → outcomes/testimonials → pricing → FAQ → CTA.

## Snippets
Hero:
```html
<section class="max-w-5xl mx-auto px-6 pt-16 pb-10 text-center">
  <span class="text-xs px-3 py-1 rounded-full bg-[#EEF0FE] text-[#4F46E5]">New cohort · Starts May 6</span>
  <h1 class="text-4xl md:text-5xl font-bold text-[#1B1B2E] mt-5">Become a Data Analyst in 12 weeks.</h1>
  <p class="mt-4 text-[#63637A] max-w-xl mx-auto">Project-based, mentor-led, job-ready.</p>
  <a class="inline-block mt-8 px-7 py-3 rounded-xl bg-[#4F46E5] text-white font-medium">Enroll now</a>
  <div class="mt-8 flex justify-center gap-8 text-sm text-[#63637A]"><span>★ 4.9 (2.1k)</span><span>14,000 students</span><span>48 hrs</span></div>
</section>
```
Curriculum list:
```html
<section class="max-w-3xl mx-auto px-6 py-16">
  <h2 class="text-2xl font-bold text-[#1B1B2E] mb-6">What you'll learn</h2>
  <ul class="space-y-3"><li class="flex gap-3 items-start"><!-- repeat -->
    <span class="mt-1 w-5 h-5 rounded-full bg-[#F59E0B]/20 text-[#F59E0B] grid place-items-center text-xs">✓</span>
    <span class="text-[#1B1B2E]">SQL, Python and dashboards from scratch</span></li></ul>
</section>
```

## Adaptation
Lead with a concrete outcome ("Become X in N weeks"), not "learn stuff". Stats row (rating +
students + duration) builds trust. Curriculum with checkmarks + instructor card + pricing +
FAQ are expected. Friendly indigo, warm accent on progress. Keep it encouraging.
