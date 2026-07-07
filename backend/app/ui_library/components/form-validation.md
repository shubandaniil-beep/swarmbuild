---
id: form-validation
name: Contact form + validation
kind: component
triggers: form, contact, signup, sign up, subscribe, validation, форм, контакт, заявк, регистрац, подписк, валидац, обратн, связ, заполн
summary: Accessible contact/signup form with inline validation, error messages, success state.
---

# Component: Contact form + validation
Contact / signup / lead form with client-side validation, inline errors and a success
message. Recolor to page tokens. Wire `action`/fetch to a real endpoint when available.

```html
<form id="cform" novalidate class="max-w-md mx-auto space-y-4">
  <div>
    <label class="block text-sm mb-1">Name</label>
    <input name="name" required class="w-full px-3 py-2 rounded-lg border"/>
    <p data-err="name" class="text-xs text-red-600 mt-1 hidden">Please enter your name.</p>
  </div>
  <div>
    <label class="block text-sm mb-1">Email</label>
    <input name="email" type="email" required class="w-full px-3 py-2 rounded-lg border"/>
    <p data-err="email" class="text-xs text-red-600 mt-1 hidden">Enter a valid email.</p>
  </div>
  <button class="w-full py-2 rounded-lg bg-black text-white">Send</button>
  <p data-success class="text-sm text-green-600 hidden">Thanks — we'll be in touch!</p>
</form>
<script>
document.getElementById('cform').addEventListener('submit',function(e){
  e.preventDefault(); let ok=true; const f=e.target;
  const fail=(n,c)=>{const p=f.querySelector('[data-err="'+n+'"]');p.classList.toggle('hidden',c);if(!c)ok=false};
  fail('name', f.name.value.trim()!=='');
  fail('email', /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.value));
  if(ok){ f.querySelector('[data-success]').classList.remove('hidden'); f.reset(); }
});
</script>
```

Usage: add fields as `input + [data-err="<name>"]` pairs and a matching `fail()` check.
Replace the success block with a real `fetch(action)` POST when a backend exists.
React: hold values + errors in state, validate on submit, render the same markup.
