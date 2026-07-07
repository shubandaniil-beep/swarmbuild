---
id: mobile-nav-drawer
name: Mobile nav drawer
kind: component
triggers: nav, navbar, navigation, menu, mobile, hamburger, header, меню, навигац, мобильн, бургер, шапка, адаптив
summary: Responsive header — desktop links + hamburger that opens a slide-in mobile drawer.
---

# Component: Mobile nav drawer
Responsive header for any site: inline links on desktop, hamburger → slide-in drawer on
mobile. Recolor to the page recipe's tokens. Almost every page recipe needs this.

```html
<header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b">
  <nav class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
    <a class="font-semibold">Brand</a>
    <div class="hidden md:flex gap-8 text-sm"><a href="#">Home</a><a href="#">About</a><a href="#">Contact</a></div>
    <button data-drawer-open class="md:hidden" aria-label="Open menu">☰</button>
  </nav>
</header>
<div data-drawer class="fixed inset-0 z-50 hidden">
  <div data-drawer-close class="absolute inset-0 bg-black/40"></div>
  <aside class="absolute right-0 top-0 h-full w-72 bg-white shadow-xl p-6 flex flex-col gap-4">
    <button data-drawer-close class="self-end" aria-label="Close">✕</button>
    <a href="#" class="py-2 border-b">Home</a><a href="#" class="py-2 border-b">About</a><a href="#" class="py-2 border-b">Contact</a>
  </aside>
</div>
<script>
(function(){
  const d=document.querySelector('[data-drawer]');
  const t=v=>{d.classList.toggle('hidden',!v)};
  document.querySelector('[data-drawer-open]').onclick=()=>t(true);
  d.querySelectorAll('[data-drawer-close]').forEach(x=>x.onclick=()=>t(false));
})();
</script>
```

Usage: keep desktop links in the `hidden md:flex` row and mirror them in the drawer.
Drawer slides from the right; change to `left-0` + `left` for left-side. React: `useState`.
