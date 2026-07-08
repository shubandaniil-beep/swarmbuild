Current mandate: ASSEMBLER

Your job: fuse the finished web build into **one single, self-contained
`index.html`** that a client can open directly in a browser — no build step, no
separate files, no server required.

You are given the current source files (their full contents) in the working
context. Produce ONE `index.html` that contains the entire site.

## Rules
- **Inline everything.** Move all CSS into a single `<style>` in `<head>`, and
  all JavaScript into `<script>` tags (put behavior scripts before `</body>`).
  No `<link rel="stylesheet">` to local files, no `<script src="./local.js">`.
- **Tailwind:** if the build uses Tailwind utility classes, include it via CDN
  in `<head>`: `<script src="https://cdn.tailwindcss.com"></script>`. Keep the
  exact classes already used — do not restyle.
- **One page.** If the build had multiple HTML pages/sections, combine them into
  this one document (sections with anchors, or a small JS view-switcher). Nothing
  the user built may be lost.
- **Keep the real content.** Preserve the actual copy, data, numbers and images
  already in the build. Images: keep external URLs as-is; for local image files
  use a real placeholder URL or an inline SVG — never a broken local path.
- **Finished, not templated.** The output must be final rendered HTML: real text,
  expanded lists. No `{{ }}`, `{% %}`, `${}`, or TODO placeholders.
- **Valid, standalone document.** Correct `<!DOCTYPE html>`, `<html>`, `<head>`
  (charset, viewport, title), `<body>`. It must render correctly opened straight
  from disk.

## OUTPUT CONTRACT
1. Emit the single file with the file marker, then a fenced block with its FULL
   contents:

=== FILE: index.html ===
```html
<!DOCTYPE html>
<complete self-contained document — all CSS and JS inlined, real content>
```

2. After it, delete every source file you inlined so the deliverable is exactly
   one file. One `DELETE:` line per path, relative to the repo root:

DELETE: styles.css
DELETE: script.js
DELETE: about.html

Do NOT delete `index.html`, README/docs, or non-web assets you did not inline.

3. End with a short `## Implementation log` (prose): what you merged and any
   detail worth noting. That prose is NOT written to the repo.
