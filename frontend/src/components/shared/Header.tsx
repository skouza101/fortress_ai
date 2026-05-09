"use client";

import Link from "next/link";
import { ShieldCheck, Menu, X, LogOut, User } from "lucide-react";
import { useState } from "react";
import { useSession, signOut } from "next-auth/react";

const NAV_LINKS = [
  { label: "Product", href: "/chat" },
  { label: "Benchmarks", href: "/benchmarks" },
  { label: "Help", href: "/help" },
];

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: session, status } = useSession();
  const isAuthenticated = status === "authenticated";

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 border-b border-white/10 bg-background/80 backdrop-blur-2xl">
      <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shadow-[0_0_10px_rgba(24,86,255,0.15)] group-hover:bg-primary/20 transition-colors">
            <ShieldCheck className="w-5 h-5 text-primary" />
          </div>
          <span className="font-bold text-lg tracking-wide text-secondary">
            FORTRESS AI
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-muted-foreground hover:text-secondary transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Desktop Auth */}
        <div className="hidden md:flex items-center gap-3">
          {status === "loading" ? (
            <div className="h-9 w-40 rounded-xl bg-white/5 border border-white/10 animate-pulse" aria-hidden="true" />
          ) : isAuthenticated ? (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
                <User className="w-4 h-4 text-primary" />
                <span className="text-xs font-medium text-secondary truncate max-w-[120px]">
                  {session?.user?.email}
                </span>
              </div>
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-red-400 transition-colors px-3 py-2"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="text-sm font-medium text-muted-foreground hover:text-secondary transition-colors px-4 py-2"
              >
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                className="glass-button text-sm font-semibold px-5 py-2.5 rounded-xl"
              >
                Get Started
              </Link>
            </>
          )}
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-white/5 text-muted-foreground"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/10 bg-background/95 backdrop-blur-2xl px-6 py-4 space-y-3">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block text-sm font-medium text-muted-foreground hover:text-secondary py-2"
            >
              {link.label}
            </Link>
          ))}
          <div className="flex gap-3 pt-3 border-t border-white/10">
            {status === "loading" ? (
              <div className="w-full h-10 rounded-xl bg-white/5 border border-white/10 animate-pulse" aria-hidden="true" />
            ) : isAuthenticated ? (
              <button
                onClick={() => {
                  setMobileOpen(false);
                  signOut({ callbackUrl: "/" });
                }}
                className="flex-1 flex items-center justify-center gap-2 text-sm font-medium text-red-400 py-2.5 rounded-xl border border-red-400/20 hover:bg-red-400/10 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            ) : (
              <>
                <Link href="/auth/login" onClick={() => setMobileOpen(false)} className="flex-1 text-center text-sm font-medium text-muted-foreground py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors">
                  Sign In
                </Link>
                <Link href="/auth/signup" onClick={() => setMobileOpen(false)} className="flex-1 text-center glass-button text-sm font-semibold py-2.5 rounded-xl">
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
