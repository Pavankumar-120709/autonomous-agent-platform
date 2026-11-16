import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Autonomous Agent Platform | Bounded Execution & Step-Level Logging",
  description: "Production-grade Autonomous Research Agent with LangGraph, PostgreSQL Step Persistence, and SSE Live Tracing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">{children}</main>
        <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground font-mono">
          Autonomous Agent Platform &bull; LangGraph Engine &bull; PostgreSQL Step-Level Observability &bull; SSRF Safe
        </footer>
      </body>
    </html>
  );
}
