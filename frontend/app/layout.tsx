import "./globals.css";
import type { ReactNode } from "react";
import NavBar from "@/components/NavBar";

export const metadata = {
  title: "SwarmBuild AI",
  description: "AI Project Factory for business files, MVP packages, and launch materials",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <NavBar />
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
