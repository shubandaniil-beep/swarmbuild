---
id: toast-notification
name: Toast notification
kind: component
triggers: toast, notification, notify, alert, snackbar, уведомлен, тост, оповещен, сообщен об успех
summary: Transient toast messages (success/error) that stack and auto-dismiss.
---

# Component: Toast notification
Small transient messages for "Saved", "Error", "Copied". Stacks bottom-right and
auto-dismisses. Call `toast(msg, type)` from anywhere. Recolor to page tokens.

```html
<div id="toasts" class="fixed bottom-4 right-4 z-50 flex flex-col gap-2"></div>
<button onclick="toast('Saved!','success')" class="px-4 py-2 rounded-lg bg-black text-white">Demo</button>
<script>
function toast(msg,type='success'){
  const wrap=document.getElementById('toasts');
  const el=document.createElement('div');
  const color=type==='error'?'bg-red-600':type==='success'?'bg-green-600':'bg-gray-800';
  el.className='text-white text-sm px-4 py-2 rounded-lg shadow-lg '+color+' opacity-0 translate-y-2 transition';
  el.textContent=msg; wrap.appendChild(el);
  requestAnimationFrame(()=>el.classList.remove('opacity-0','translate-y-2'));
  setTimeout(()=>{el.classList.add('opacity-0','translate-y-2');setTimeout(()=>el.remove(),300)},3000);
}
</script>
```

Usage: call `toast('Message','success'|'error'|'info')` after form submits, copies, saves.
React: keep a toasts array in state (or a small context/provider) and render the list.
