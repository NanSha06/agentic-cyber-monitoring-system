import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title:       "CyberBattery Intelligence Platform",
  description: "Agentic ML-powered risk intelligence for cyber-physical battery assets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
