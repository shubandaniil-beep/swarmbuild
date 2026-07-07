---
id: carousel-slider
name: Carousel / slider
kind: component
triggers: carousel, slider, slideshow, gallery, testimonials, карусель, слайдер, галере, отзыв, слайд, листа
summary: Scroll-snap carousel with prev/next buttons — for galleries, testimonials, logos.
---

# Component: Carousel / slider
Horizontal slider for galleries, testimonials, product shots. Uses CSS scroll-snap (smooth,
touch-friendly) with prev/next buttons. Recolor to page tokens.

```html
<div class="relative max-w-4xl mx-auto px-6">
  <div data-track class="flex gap-4 overflow-x-auto snap-x snap-mandatory scroll-smooth pb-2 [scrollbar-width:none]">
    <!-- repeat slides -->
    <div class="snap-start shrink-0 w-full md:w-1/2 aspect-video bg-gray-200 rounded-xl grid place-items-center">Slide 1</div>
    <div class="snap-start shrink-0 w-full md:w-1/2 aspect-video bg-gray-200 rounded-xl grid place-items-center">Slide 2</div>
    <div class="snap-start shrink-0 w-full md:w-1/2 aspect-video bg-gray-200 rounded-xl grid place-items-center">Slide 3</div>
  </div>
  <button data-prev class="absolute left-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white shadow grid place-items-center">‹</button>
  <button data-next class="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-white shadow grid place-items-center">›</button>
</div>
<script>
(function(){
  const t=document.querySelector('[data-track]');
  const step=()=>t.clientWidth*0.9;
  document.querySelector('[data-next]').onclick=()=>t.scrollBy({left:step(),behavior:'smooth'});
  document.querySelector('[data-prev]').onclick=()=>t.scrollBy({left:-step(),behavior:'smooth'});
})();
</script>
```

Usage: add slides inside `[data-track]`; width `w-full`/`md:w-1/2` controls how many show.
Great for testimonials (swap slide content for quote cards). React: use a ref + `scrollBy`.
