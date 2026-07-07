---
id: admin-dashboard
name: Console — analytics dashboard
domain: dashboard, admin, analytics, crm, saas, panel, дашборд, админ, аналитик, панель, статистик
style: functional, clean, data-dense, modern, чист, функционал
colors: blue, neutral, light, син, светл
tags: dashboard, admin, analytics, crm, panel, sidebar, stats, charts, table, kpi, дашборд, админ, панель, аналитик, таблиц, графики
stack: html, tailwind
summary: Light admin dashboard — sidebar nav, KPI stat cards, chart area, data table.
---

# Console — analytics dashboard
For admin panels, analytics, CRM, internal tools. Clarity and density over decoration.
Sidebar + topbar + content grid.

## Tokens
bg `#F6F7F9` · surface `#FFF` · border `#E7E9ED` · text `#1A1D23` · muted `#6B7280` ·
primary `#2F6BFF` · positive `#16A34A` · negative `#DC2626`. Font Inter, 14px base.
Cards `rounded-xl border shadow-sm`. Sidebar `w-60`. Numbers `tabular-nums`.

## Layout order
fixed sidebar (logo + nav groups) → topbar (search + user) → KPI row (4 stat cards) →
chart panel (2/3) + list panel (1/3) → data table with header + row actions.

## Snippets
Shell + KPI card:
```html
<div class="flex min-h-screen">
  <aside class="w-60 bg-white border-r border-[#E7E9ED] p-4">
    <div class="font-semibold mb-6">Console</div>
    <nav class="space-y-1 text-sm">
      <a class="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#EEF3FF] text-[#2F6BFF]">Overview</a>
      <a class="flex items-center gap-2 px-3 py-2 rounded-lg text-[#6B7280] hover:bg-[#F6F7F9]">Customers</a>
    </nav></aside>
  <main class="flex-1 p-6">
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-[#E7E9ED] shadow-sm p-4"><!-- repeat -->
        <p class="text-sm text-[#6B7280]">Revenue</p>
        <p class="text-2xl font-semibold tabular-nums mt-1">$48,210</p>
        <p class="text-xs text-[#16A34A] mt-1">▲ 12.4%</p></div>
    </div>
  </main>
</div>
```
Data table:
```html
<table class="w-full mt-6 bg-white rounded-xl border border-[#E7E9ED] text-sm">
  <thead class="text-left text-[#6B7280] border-b border-[#E7E9ED]">
    <tr><th class="px-4 py-3 font-medium">Customer</th><th class="px-4 py-3 font-medium">Status</th><th class="px-4 py-3 font-medium">MRR</th></tr></thead>
  <tbody><tr class="border-b border-[#E7E9ED] last:border-0 hover:bg-[#F6F7F9]">
    <td class="px-4 py-3">Acme Inc</td>
    <td class="px-4 py-3"><span class="px-2 py-0.5 rounded-full bg-[#E7F6EC] text-[#16A34A] text-xs">Active</span></td>
    <td class="px-4 py-3 tabular-nums">$1,200</td></tr></tbody>
</table>
```

## Adaptation
Sidebar + KPI row + chart + table is the skeleton — always present. Use `tabular-nums` on
numbers, status pills for states, green/red for deltas. For charts, leave a placeholder div
and note the lib (Chart.js/Recharts). Keep it light unless a dark theme is requested.
