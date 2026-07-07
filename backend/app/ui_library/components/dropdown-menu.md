---
id: dropdown-menu
name: Dropdown menu
kind: component
triggers: dropdown, select, menu, filter, user menu, выпадающ, дропдаун, выбор, фильтр, профиль
summary: Click-to-open dropdown (user menu, filters, actions) that closes on outside click.
---

# Component: Dropdown menu
Click-to-toggle menu for user/account menus, filters, row actions. Closes on outside
click and Esc. Recolor to page tokens.

```html
<div data-dd class="relative inline-block text-left">
  <button data-dd-btn class="px-4 py-2 rounded-lg border inline-flex items-center gap-2">
    Options <span class="text-xs">▾</span>
  </button>
  <div data-dd-menu class="hidden absolute right-0 mt-2 w-44 rounded-xl border bg-white shadow-lg py-1 z-30">
    <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-50">Profile</a>
    <a href="#" class="block px-4 py-2 text-sm hover:bg-gray-50">Settings</a>
    <a href="#" class="block px-4 py-2 text-sm text-red-600 hover:bg-gray-50">Sign out</a>
  </div>
</div>
<script>
document.querySelectorAll('[data-dd]').forEach(dd=>{
  const btn=dd.querySelector('[data-dd-btn]'), menu=dd.querySelector('[data-dd-menu]');
  btn.onclick=e=>{e.stopPropagation();menu.classList.toggle('hidden')};
  document.addEventListener('click',e=>{if(!dd.contains(e.target))menu.classList.add('hidden')});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')menu.classList.add('hidden')});
});
</script>
```

Usage: multiple dropdowns per page work (each `[data-dd]` is independent). Align the menu
with `right-0`/`left-0`. React: `useState` for open + a click-outside effect.
