---
id: tabs
name: Tabs
kind: component
triggers: tabs, tabbed, вкладк, табы, переключател, секции
summary: Accessible tab switcher — one active panel at a time, keyboard-friendly buttons.
---

# Component: Tabs
Switch between panels (features, plans, specs). Recolor active state to the page tokens.

```html
<div data-tabs>
  <div class="flex gap-1 border-b" role="tablist">
    <button data-tab="0" class="px-4 py-2 -mb-px border-b-2 border-black font-medium">Overview</button>
    <button data-tab="1" class="px-4 py-2 -mb-px border-b-2 border-transparent text-gray-500">Pricing</button>
    <button data-tab="2" class="px-4 py-2 -mb-px border-b-2 border-transparent text-gray-500">Reviews</button>
  </div>
  <div data-panel="0" class="py-6">Overview content.</div>
  <div data-panel="1" class="py-6 hidden">Pricing content.</div>
  <div data-panel="2" class="py-6 hidden">Reviews content.</div>
</div>
<script>
document.querySelectorAll('[data-tabs]').forEach(root=>{
  const tabs=root.querySelectorAll('[data-tab]'), panels=root.querySelectorAll('[data-panel]');
  tabs.forEach(t=>t.onclick=()=>{
    tabs.forEach(x=>x.className='px-4 py-2 -mb-px border-b-2 border-transparent text-gray-500');
    t.className='px-4 py-2 -mb-px border-b-2 border-black font-medium';
    panels.forEach(p=>p.classList.toggle('hidden',p.dataset.panel!==t.dataset.tab));
  });
});
</script>
```

Usage: keep `data-tab` index in sync with `data-panel`. Add tabs by adding matching
pairs. React: track `active` index in state, toggle classes and panel render off it.
