"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { useAppStore } from "@/lib/store";
import { Menu, X, Sparkles, User } from "lucide-react";
import clsx from "clsx";

const APP_NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/apply", label: "Apply" },
  { href: "/runs", label: "Runs" },
];

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const subscribed = useAppStore((state) => state.subscribed);
  const profile = useAppStore((state) => state.profile);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const candidateName = profile?.fullName || "Guest";

  return (
    <div className="min-h-screen w-full bg-canvas text-ink flex flex-col justify-between">
      {/* Optional Light Guard Banner if not subscribed */}
      {!subscribed && (
        <div className="bg-cream border-b border-line px-4 py-2 text-center text-xs font-medium text-body">
          <span>You are previewing the demo. </span>
          <Link
            href="/subscribe"
            className="text-accent font-semibold hover:underline ml-1 inline-flex items-center gap-1"
          >
            <span>Subscribe for $79 to unlock autopilot</span>
            <Sparkles className="w-3 h-3" />
          </Link>
        </div>
      )}

      {/* Top App Bar */}
      <header className="sticky top-0 z-30 bg-canvas/95 backdrop-blur-md border-b border-line">
        <Container className="flex items-center justify-between h-16 sm:h-18">
          {/* Left: Logo */}
          <div className="flex items-center shrink-0">
            <Logo href="/" />
          </div>

          {/* Center: Desktop Navigation Links */}
          <nav className="hidden md:flex items-center justify-center gap-2 text-sm font-medium text-body flex-1">
            {APP_NAV_LINKS.map(({ href, label }) => {
              const isActive = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={label}
                  href={href}
                  className={clsx(
                    "px-3.5 py-1.5 rounded-pill transition-all outline-none focus-visible:ring-2 focus-visible:ring-accent",
                    isActive
                      ? "text-accent font-semibold bg-accent-soft/70 shadow-3xs"
                      : "text-body hover:text-ink hover:bg-cream"
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Right: Profile Chip & Mobile Menu Toggle */}
          <div className="flex items-center gap-3">
            {/* Candidate Profile Chip */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-pill border border-line bg-canvas shadow-3xs">
              <div className="w-6 h-6 rounded-full bg-accent-soft text-accent flex items-center justify-center">
                <User className="w-3.5 h-3.5 stroke-[2.5]" />
              </div>
              <span className="text-xs sm:text-sm font-medium text-ink max-w-[120px] sm:max-w-[160px] truncate">
                {candidateName}
              </span>
              <span className="text-[10px] font-bold text-accent bg-accent-soft px-2 py-0.5 rounded-pill uppercase tracking-wider">
                Pro
              </span>
            </div>

            {/* Mobile Menu Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-body hover:text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg"
              aria-label="Toggle navigation"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </Container>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-canvas border-b border-line px-6 py-4 flex flex-col gap-2 animate-in fade-in duration-150">
            {APP_NAV_LINKS.map(({ href, label }) => {
              const isActive = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={label}
                  href={href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={clsx(
                    "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "text-accent font-semibold bg-accent-soft/70"
                      : "text-body hover:text-ink hover:bg-cream"
                  )}
                >
                  {label}
                </Link>
              );
            })}
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full py-8 sm:py-12">
        <Container>{children}</Container>
      </main>

      {/* Compact App Footer */}
      <footer className="border-t border-line py-6 text-center text-xs text-muted">
        <Container>
          JobFlow Application Automation Console &bull; Background queue active
        </Container>
      </footer>
    </div>
  );
}
