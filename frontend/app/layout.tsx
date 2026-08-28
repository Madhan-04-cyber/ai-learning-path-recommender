import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PathMind AI | Adaptive Learning GPS",
  description: "A dependency-aware, skill-gap-based learning path engine.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
