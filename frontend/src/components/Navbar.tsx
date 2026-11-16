"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Cpu, BarChart3, History, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { label: "Playground", href: "/", icon: Cpu },
    { label: "Run History", href: "/#history", icon: History },
    { label: "Platform Analytics", href: "/analytics", icon: BarChart3 },
  ];

  return (
    <header className="border-b border-border bg-card/60 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
              Autonomous Agent Platform
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 uppercase font-mono">
                v1.0
              </span>
            </div>
            <p className="text-xs text-muted-foreground hidden sm:block">
              Bounded LangGraph State Machine & Step-Level Logging
            </p>
          </div>
        </Link>

        <nav className="flex items-center gap-2 sm:gap-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                  active
                    ? "bg-secondary text-foreground border border-border"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}

          <div className="ml-2 pl-3 border-l border-border flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
            <ShieldCheck className="w-4 h-4" />
            <span className="hidden md:inline">SSRF Safe</span>
          </div>
        </nav>
      </div>
    </header>
  );
}
