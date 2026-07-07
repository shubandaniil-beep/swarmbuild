---
id: gaming-neon
name: Arcade — gaming / esports
domain: gaming, game, esports, streamer, twitch, clan, guild, nft game, arcade, игры, игра, киберспорт, стример, клан, гейминг
style: dark, neon, energetic, futuristic, edgy, темн, неон, дерзк, футуризм
colors: dark, neon, magenta, cyan, purple, темн, неон, циан, маджента
tags: gaming, game, esports, streamer, twitch, clan, guild, arcade, roster, tournament, join, игры, киберспорт, стример, клан, турнир, гейминг
stack: html, tailwind
summary: Dark neon gaming/esports site — glowing accents, hero with game art, roster, tournaments, join.
---

# Arcade — gaming / esports
For games, esports teams, streamers, clans, gaming products. Dark, neon-lit, high-energy,
edgy. Glow effects and angular type. Use when brief says gaming/esports/streamer.

## Tokens
bg `#0A0710` · surface `#140B1E` · text `#F0EAFF` · muted `#9A8CB8` · neon-magenta `#FF2E97` ·
neon-cyan `#22D3EE` · border `#2A1B3D`. Font Orbitron/Chakra Petch headings, Inter body.
Glow: `shadow-[0_0_20px_#FF2E97]`. UPPERCASE headings. Sharp `rounded-md`. Neon on CTAs/edges only.

## Layout order
nav (+ glowing Join) → hero (game art bg + glowing title + play/join CTA) → stats/roster grid →
upcoming tournaments/schedule → feature/game modes → community/Discord CTA → footer.

## Snippets
Hero:
```html
<section class="relative overflow-hidden"><div class="h-[80vh]"><img src="/game.jpg" class="w-full h-full object-cover opacity-60"/></div>
  <div class="absolute inset-0 bg-gradient-to-t from-[#0A0710] via-transparent"></div>
  <div class="absolute inset-0 flex flex-col justify-center px-6 max-w-6xl mx-auto">
    <p class="text-[#22D3EE] tracking-[0.3em] text-sm">SEASON 4 · LIVE</p>
    <h1 class="text-5xl md:text-7xl font-extrabold uppercase text-[#F0EAFF] mt-3" style="text-shadow:0 0 24px #FF2E97">Enter the arena</h1>
    <a class="mt-8 w-fit px-8 py-3 rounded-md bg-[#FF2E97] text-white font-bold uppercase shadow-[0_0_24px_#FF2E97] hover:scale-105 transition">Play free</a>
  </div>
</section>
```
Roster / tournament card:
```html
<article class="rounded-md border border-[#2A1B3D] bg-[#140B1E] p-4 hover:border-[#FF2E97] hover:shadow-[0_0_20px_#FF2E97]/40 transition"><!-- roster -->
  <div class="aspect-square bg-[#2A1B3D] rounded"></div>
  <p class="text-[#F0EAFF] font-bold uppercase mt-3">Sh4dow</p><p class="text-xs text-[#9A8CB8]">Duelist · #12</p></article>
<div class="flex items-center justify-between border border-[#2A1B3D] rounded-md p-4"><!-- tournament -->
  <div><p class="text-[#F0EAFF] font-bold uppercase">Winter Clash</p><p class="text-sm text-[#9A8CB8]">Feb 20 · $10k prize</p></div>
  <a class="px-4 py-2 rounded bg-[#22D3EE] text-[#0A0710] font-bold text-sm uppercase">Register</a></div>
```

## Adaptation
Dark base + neon magenta/cyan glow on CTAs, borders, hover — never flood everything with neon.
UPPERCASE display headings with text-shadow glow. Roster grid + tournaments/schedule + a
community (Discord) CTA are expected. Game/character art in the hero. Keep it edgy and alive.
