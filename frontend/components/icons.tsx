/**
 * Единая система иконок: stroke-based, 24×24, currentColor.
 * Никаких эмодзи в продукте — только векторные знаки.
 */
import type { SVGProps } from "react";

const PATHS = {
  bolt: "M13 2 4.5 13.5H11L10 22l9.5-11.5H13L13 2Z",
  code: "m8 7-5 5 5 5m8-10 5 5-5 5",
  file: "M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7L14 2Zm0 0v5h5",
  fileText: "M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7L14 2Zm0 0v5h5M9 13h6M9 17h4",
  briefcase: "M4 8h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Zm5 0V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-12 5h18",
  layers: "m12 3 9 5-9 5-9-5 9-5Zm-9 10 9 5 9-5",
  sparkles: "M12 4l1.8 4.2L18 10l-4.2 1.8L12 16l-1.8-4.2L6 10l4.2-1.8L12 4Zm7 11 .7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7.7-1.8Z",
  package: "M12 3l9 4.5v9L12 21l-9-4.5v-9L12 3Zm-9 4.5 9 4.5 9-4.5M12 12v9",
  bookOpen: "M2 4h7a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H2V4Zm20 0h-7a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h7V4Z",
  wrench: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z",
  mic: "M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3Zm-7 8v1a7 7 0 0 0 14 0v-1m-7 8v4",
  flask: "M10 2v6.5L4.5 18a2 2 0 0 0 1.7 3h11.6a2 2 0 0 0 1.7-3L14 8.5V2m-5.5 0h7M7 15h10",
  megaphone: "m3 11 18-6v12L3 13v-2Zm4 2.5V19a2 2 0 0 0 2 2h1v-7",
  trendingUp: "M22 7l-8.5 8.5-5-5L2 17M16 7h6v6",
  rocket: "M12 15c5.2-3.5 6-8.3 6-11-2.7 0-7.5.8-11 6m5 5-3-3m3 3-2 4-3-1-1-3-4-2 4-2m9-1a1.5 1.5 0 1 0 2-2M6 18c-1 1-1.5 4-1.5 4S7.5 21.5 8.5 20.5",
  map: "M9 3 3.6 5.4A1 1 0 0 0 3 6.3v13a.5.5 0 0 0 .7.5L9 17.5l6 3 5.4-2.4a1 1 0 0 0 .6-.9v-13a.5.5 0 0 0-.7-.5L15 6 9 3Zm0 0v14.5M15 6v14.5",
  alertTriangle: "m10.3 3.9-8.2 14.2a2 2 0 0 0 1.7 3h16.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0ZM12 9v4m0 4h.01",
  arrowRight: "M5 12h14m-6-6 6 6-6 6",
  receipt: "M5 2h14v20l-2.3-1.5L14.4 22l-2.4-1.5L9.6 22l-2.3-1.5L5 22V2Zm4 6h6m-6 4h6m-6 4h3",
  ruler: "M21.3 8.7 15.3 2.7a1 1 0 0 0-1.4 0L2.7 13.9a1 1 0 0 0 0 1.4l6 6a1 1 0 0 0 1.4 0L21.3 10.1a1 1 0 0 0 0-1.4ZM7.5 10.5 9 12m1.5-4.5L12 9m1.5-4.5L15 6",
  penLine: "M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4m4-5 5 5 5-5m-5 5V3",
  play: "m7 5 12 7-12 7V5Z",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18M6 6l12 12",
  search: "M11 5a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm10 16-4.8-4.8",
  scale: "M12 3v18m-5 0h10M3 7h3c2 0 4.5-.7 6-1.6 1.5.9 4 1.6 6 1.6h3M6 7l-3 7a3.4 3.4 0 0 0 6 0L6 7Zm12 0-3 7a3.4 3.4 0 0 0 6 0l-3-7Z",
  inbox: "M22 13h-5.5l-2 3h-5l-2-3H2m3.4-7.9L2 13v5a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5l-3.4-7.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.8 1.1Z",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l3 2",
  plug: "M12 22v-4M9 8V3m6 5V3M6 8h12v5a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5V8Z",
  creditCard: "M3 6h18a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Zm-1 4h20",
  circleDot: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 6.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z",
  hexagon: "M12 2.5 20 7v10l-8 4.5L4 17V7l8-4.5Z",
  send: "m22 2-7 20-4-9-9-4 20-7Zm0 0L11 13",
  globe: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-9 9h18M12 3c2.5 2.5 3.8 5.6 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.6-3.8-9S9.5 5.5 12 3Z",
  presentation: "M3 3h18M4 3v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V3M12 15v3m-4 4 4-4 4 4",
  clipboardCheck: "M9 4h6v3H9V4Zm7 1h2a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m1 9 2 2 4-4",
  shield: "M12 2 5 5v6c0 5 3 8.5 7 10 4-1.5 7-5 7-10V5l-7-3Z",
  refresh: "M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 16,
  strokeWidth = 1.7,
  ...props
}: { name: IconName; size?: number; strokeWidth?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

/** Квадратик с иконкой — базовый «пиксель» карточек продукта. */
export function IconTile({
  name,
  size = 34,
  className = "",
}: { name: IconName; size?: number; className?: string }) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-lg border border-amber-400/20
        bg-amber-400/8 text-amber-300 ${className}`}
      style={{ width: size, height: size }}
    >
      <Icon name={name} size={Math.round(size * 0.5)} />
    </span>
  );
}
