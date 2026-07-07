---
id: docs-site
name: Manual — documentation site
domain: documentation, docs, api reference, api docs, knowledge base, developer docs, guide, help center, документац, справоч, руководств, база знан, гайд, разработчик
style: clean, functional, readable, technical, чист, технич, читаем
colors: neutral, blue, light, нейтрал, син, светл
tags: documentation, docs, api reference, api docs, knowledge base, guide, developer docs, sidebar, changelog, документац, справоч, руководств, гайд, база знан, разработчик
stack: html, tailwind
summary: Docs site — left nav tree, readable content column, right on-page TOC, code blocks, search.
---

# Manual — documentation site
For product docs, API references, knowledge bases, developer guides, help centers. Structure
+ readability + fast navigation. Three columns on desktop.

## Tokens
bg `#FFF` · sidebar `#FAFBFC` · text `#1B2230` · muted `#647084` · primary `#2563EB` ·
code-bg `#0F172A` · border `#E9ECF1`. Font Inter; body 16px/1.7. Content `max-w-[46rem]`.
Code `font-mono text-sm`. Sidebar `w-64`.

## Layout order
top bar (logo + search + version) → [left nav tree | content (max-w-46rem) | right on-page TOC].
Content: h1, prose, callouts, code blocks, prev/next links.

## Snippets
Shell:
```html
<header class="h-14 border-b flex items-center px-6 gap-4">
  <span class="font-semibold">Manual</span>
  <input placeholder="Search docs (⌘K)" class="ml-4 w-72 px-3 py-1.5 rounded-lg border text-sm"/>
</header>
<div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-[16rem_1fr_14rem] gap-8 px-6 py-8">
  <aside class="hidden lg:block text-sm">
    <p class="font-semibold text-[#1B2230] mb-2">Getting started</p>
    <nav class="space-y-1 border-l border-[#E9ECF1]">
      <a class="block pl-3 -ml-px border-l-2 border-[#2563EB] text-[#2563EB]">Installation</a>
      <a class="block pl-3 -ml-px border-l-2 border-transparent text-[#647084] hover:text-[#1B2230]">Quick start</a>
    </nav></aside>
  <main class="max-w-[46rem]">
    <h1 class="text-3xl font-bold text-[#1B2230]">Installation</h1>
    <p class="mt-4 text-[#374151]">Install the package with your manager of choice.</p>
    <pre class="mt-4 rounded-xl bg-[#0F172A] text-[#E2E8F0] p-4 text-sm overflow-x-auto"><code>npm install manual</code></pre>
    <div class="mt-6 rounded-lg border-l-4 border-[#2563EB] bg-[#EFF4FF] p-4 text-sm">💡 Tip: use Node 18+.</div>
  </main>
  <aside class="hidden lg:block text-sm text-[#647084]">
    <p class="font-medium mb-2">On this page</p><a class="block hover:text-[#1B2230]">Requirements</a><a class="block hover:text-[#1B2230]">Install</a></aside>
</div>
```

## Adaptation
Three columns: nav tree (active item highlighted with left border) + readable content
(`max-w-[46rem]`, 16px) + on-page TOC. Dark code blocks, colored callout boxes, prev/next at
the bottom. Add a search box in the top bar. Prioritize clarity over decoration.
