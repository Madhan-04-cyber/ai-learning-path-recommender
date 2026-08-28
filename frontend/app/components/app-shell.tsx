"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Search, Sparkles, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { allNavigation, primaryNavigation, secondaryNavigation, type NavigationItem } from "./navigation";

function NavLink({ item, mobile = false }: { item: NavigationItem; mobile?: boolean }) {
  const pathname = usePathname();
  const active = pathname === item.href;
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      aria-label={mobile ? item.label : undefined}
      className={mobile
        ? `flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-1.5 py-2 text-center text-[10px] font-bold leading-none transition-colors ${active ? "text-emerald-400" : "text-slate-500 hover:text-slate-300"}`
        : `flex items-center gap-3 rounded-lg px-3 py-2.5 text-xs font-bold transition-colors ${active ? "bg-emerald-400 text-slate-950" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}
    >
      <Icon className={mobile ? "h-4 w-4" : "h-4 w-4"} />
      <span className={mobile ? "max-w-full leading-tight" : ""}>{item.label}</span>
    </Link>
  );
}

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-800 bg-slate-950 px-4 py-6 md:flex">
      <Link href="/home" className="mb-8 block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/80">
        <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> PathMind AI</span>
        <span className="mt-2 block text-xs text-slate-500">Your career learning GPS</span>
      </Link>
      <p className="mb-2 px-3 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-600">Main</p>
      <nav className="space-y-1" aria-label="Main navigation">{primaryNavigation.map((item) => <NavLink key={item.href} item={item} />)}</nav>
      <div className="my-6 border-t border-slate-800" />
      <p className="mb-2 px-3 text-[9px] font-bold uppercase tracking-[0.18em] text-slate-600">Explore</p>
      <nav className="space-y-1" aria-label="Secondary navigation">{secondaryNavigation.map((item) => <NavLink key={item.href} item={item} />)}</nav>
      <div className="mt-auto rounded-xl border border-slate-800 bg-slate-900/70 p-3">
        <p className="text-[9px] font-bold uppercase tracking-wider text-slate-500">Current goal</p>
        <p className="mt-1 text-xs font-bold text-white">Backend AI Developer</p>
        <p className="mt-2 text-[10px] text-emerald-400">0% career ready</p>
      </div>
    </aside>
  );
}

export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex min-w-0 items-center justify-between gap-4 border-b border-slate-800 px-4 py-4 md:px-8">
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">PathMind AI</p>
        <h1 className="mt-1 break-words text-xl font-black leading-tight text-white md:text-2xl">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        <button className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-[10px] text-slate-500 sm:flex hover:border-slate-700 hover:text-slate-200" aria-label="Search"><Search className="h-3.5 w-3.5" /> Search</button>
        <button className="rounded-lg border border-slate-800 p-2 text-slate-400 transition-colors hover:border-slate-700 hover:text-white" aria-label="Notifications"><Bell className="h-4 w-4" /></button>
        <Link href="/coach" className="hidden items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-[10px] font-bold text-white transition-colors hover:bg-indigo-500 sm:flex"><span>Ask</span> AI Coach</Link>
        <Link href="/profile" className="rounded-lg border border-slate-800 p-2 text-slate-400 transition-colors hover:border-slate-700 hover:text-white" aria-label="Profile"><UserRound className="h-4 w-4" /></Link>
      </div>
    </header>
  );
}

export function MobileNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex gap-1 border-t border-slate-800 bg-slate-950/96 px-2 pb-[calc(env(safe-area-inset-bottom)+0.5rem)] pt-2 backdrop-blur md:hidden"
      aria-label="Mobile navigation"
    >
      {primaryNavigation.map((item) => <NavLink key={item.href} item={item} mobile />)}
    </nav>
  );
}

export function AppShell({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 md:pl-64">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-slate-900 focus:px-4 focus:py-2 focus:text-sm focus:text-white">
        Skip to content
      </a>
      <Sidebar />
      <TopBar title={title} />
      <main id="main-content" className="mx-auto min-w-0 max-w-7xl p-4 pb-24 md:p-8 md:pb-8">{children}</main>
      <MobileNav />
    </div>
  );
}

export { allNavigation };
