---
id: modal-dialog
name: Modal / dialog
kind: component
triggers: modal, popup, dialog, lightbox, окно, модал, попап, диалог, всплыва
summary: Accessible modal overlay — open/close, backdrop click, Esc to close, focus-safe.
---

# Component: Modal / dialog
Drop-in overlay for confirmations, sign-up, product quick-view. Closes on backdrop
click and Esc. Match colors to the page recipe's tokens.

```html
<button data-modal-open="demo" class="px-4 py-2 rounded-lg bg-black text-white">Open</button>
<div id="demo" class="fixed inset-0 z-50 hidden items-center justify-center p-4" role="dialog" aria-modal="true">
  <div data-modal-backdrop class="absolute inset-0 bg-black/50"></div>
  <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
    <button data-modal-close class="absolute top-3 right-3 text-gray-400 hover:text-black" aria-label="Close">✕</button>
    <h2 class="text-lg font-semibold">Title</h2>
    <p class="mt-2 text-sm text-gray-600">Modal body content.</p>
    <div class="mt-6 flex justify-end gap-2">
      <button data-modal-close class="px-4 py-2 rounded-lg border">Cancel</button>
      <button class="px-4 py-2 rounded-lg bg-black text-white">Confirm</button>
    </div>
  </div>
</div>
<script>
(function(){
  const show=el=>{el.classList.remove('hidden');el.classList.add('flex')};
  const hide=el=>{el.classList.add('hidden');el.classList.remove('flex')};
  document.querySelectorAll('[data-modal-open]').forEach(b=>
    b.onclick=()=>show(document.getElementById(b.dataset.modalOpen)));
  document.querySelectorAll('[role=dialog]').forEach(m=>{
    m.querySelectorAll('[data-modal-close],[data-modal-backdrop]').forEach(x=>x.onclick=()=>hide(m));
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')
    document.querySelectorAll('[role=dialog]:not(.hidden)').forEach(hide)});
})();
</script>
```

Usage: `data-modal-open="<id>"` on the trigger, matching `id` on the dialog. Multiple
modals per page are fine. For React, use `useState(false)` and conditionally render.
