---
id: editorial-blog
name: Press — editorial blog / magazine
domain: blog, magazine, news, publication, media, article, блог, журнал, новости, статьи, медиа, публикация
style: editorial, typographic, readable, classic, редакцион, типограф
colors: neutral, warm-white, ink, нейтрал, беж
tags: blog, magazine, news, publication, media, article, editorial, reading, typography, feed, блог, журнал, статьи, новости, лента, чтение
stack: html, tailwind
summary: Reading-first blog/magazine — feature story, article feed, serif body, clean typography.
---

# Press — editorial blog / magazine
For blogs, magazines, news, publications. Reading comfort first: measured line length,
strong type hierarchy, minimal chrome.

## Tokens
bg `#FCFBF9` · surface `#FFF` · text `#1B1B1B` · muted `#6A6A6A` · border `#EAE7E1` ·
accent `#B4231F` (masthead red). Body serif (Georgia/Lora) 1.125rem/1.7; headings can be
sans or serif. Article measure `max-w-[68ch]`. Feed `max-w-5xl`. Radius small/none.

## Layout order
masthead (title + thin nav + date) → feature story (big headline + lede + image) →
article grid (image, category, title, excerpt) → newsletter → footer. Article page: title,
byline, `max-w-[68ch]` prose.

## Snippets
Masthead + feature:
```html
<header class="border-b border-[#EAE7E1]"><div class="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
  <a class="text-2xl font-serif tracking-tight">The Press</a>
  <nav class="hidden md:flex gap-6 text-sm text-[#6A6A6A]"><a class="hover:text-[#B4231F]">World</a><a class="hover:text-[#B4231F]">Tech</a><a class="hover:text-[#B4231F]">Culture</a></nav>
</div></header>
<section class="max-w-5xl mx-auto px-6 py-12 grid md:grid-cols-2 gap-8 items-center">
  <div><p class="text-xs uppercase tracking-widest text-[#B4231F]">Feature</p>
    <h1 class="font-serif text-4xl md:text-5xl leading-tight mt-2">The quiet return of the long read.</h1>
    <p class="mt-4 text-[#6A6A6A] text-lg">Why attention is the new luxury.</p></div>
  <div class="aspect-[4/3] bg-[#EAE7E1]"></div>
</section>
```
Article feed card:
```html
<article class="group"><!-- repeat -->
  <div class="aspect-[16/10] bg-[#EAE7E1] mb-3"></div>
  <p class="text-xs uppercase tracking-widest text-[#B4231F]">Tech</p>
  <h3 class="font-serif text-xl mt-1 group-hover:underline">Small models, big ideas</h3>
  <p class="text-sm text-[#6A6A6A] mt-2">A look at on-device inference.</p>
</article>
```

## Adaptation
Body is serif at a comfortable measure (~68ch) — this is the whole point. Category label +
headline + excerpt per card. One accent color (masthead/category). Keep chrome minimal; let
type and photography lead. Provide an article-page template with `prose max-w-[68ch]`.
