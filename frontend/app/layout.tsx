import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { JetBrains_Mono, Manrope } from "next/font/google";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";

// Manrope — геометричный гротеск с кириллицей: и заголовки, и текст.
// JetBrains Mono — цифры, статусы, терминал (тоже с кириллицей).
const sans = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans-loaded",
});
const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono-loaded",
});

export const metadata: Metadata = {
  title: {
    default: "SwarmBuild AI — фабрика проектов",
    template: "%s — SwarmBuild AI",
  },
  description:
    "Ротационный рой AI-агентов собирает проект под бюджет: код, документы, бизнес-план и честные ограничения — одним архивом.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" className={`${sans.variable} ${mono.variable}`}>
      <body className="flex min-h-screen flex-col">
        <NavBar />
        <main className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-8 flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
