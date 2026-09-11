"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { useAppStore } from "@/lib/store";
import { Menu, X, Sparkles, User, ShieldCheck, Clock, LogOut } from "lucide-react";
import clsx from "clsx";
import { getRemainingDays, revokeAccess } from "@/lib/access-code";

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
  const router = useRouter();
  const pathname = usePathname();
  const subscribed = useAppStore((state) => state.subscribed);
  const profile = useAppStore((state) => state.profile);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [accessDays, setAccessDays] = useState<number>(30);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAccessDays(getRemainingDays());

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setProfileMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const handleRevokeAccess = () => {
    if (
      window.confirm(
        "Are you sure you want to reset your access code on this device? You will need to enter the code again to regain access."
      )
    ) {
      revokeAccess();
      setProfileMenuOpen(false);
      router.replace("/accesscode");
    }
  };

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
            {/* Candidate Profile Dropdown Anchor */}
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setProfileMenuOpen((prev) => !prev)}
                className={clsx(
                  "flex items-center gap-2 px-3 py-1.5 rounded-pill border transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent",
                  profileMenuOpen
                    ? "border-accent bg-cream shadow-sm ring-1 ring-accent/30"
                    : "border-line bg-canvas hover:bg-cream/60 hover:border-line/80 shadow-3xs"
                )}
                aria-expanded={profileMenuOpen}
                aria-haspopup="true"
                aria-label="User account and access pass menu"
              >
                <div className="w-6 h-6 rounded-full bg-accent-soft text-accent flex items-center justify-center">
                  <User className="w-3.5 h-3.5 stroke-[2.5]" />
                </div>
                <span className="text-xs sm:text-sm font-medium text-ink max-w-[120px] sm:max-w-[160px] truncate">
                  {candidateName}
                </span>
                <span className="text-[10px] font-bold text-accent bg-accent-soft px-2 py-0.5 rounded-pill uppercase tracking-wider">
                  Pro
                </span>
              </button>

              {/* Profile Popover Menu */}
              {profileMenuOpen && (
                <div className="absolute right-0 mt-2 w-72 sm:w-80 rounded-2xl bg-canvas border border-line shadow-xl py-3 px-3 z-50 animate-in fade-in zoom-in-95 duration-150 space-y-3">
                  {/* Candidate summary */}
                  <div className="flex items-center gap-3 px-2 py-1.5 border-b border-line pb-2.5">
                    <div className="w-9 h-9 rounded-full bg-accent-soft text-accent flex items-center justify-center font-bold text-sm shrink-0">
                      {candidateName.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold text-ink truncate block">
                          {candidateName}
                        </span>
                        <span className="text-[9px] font-bold text-accent bg-accent-soft px-1.5 py-0.5 rounded-pill uppercase tracking-wider shrink-0">
                          Pro
                        </span>
                      </div>
                      <span className="text-xs text-muted truncate block">
                        {profile?.email || "candidate@jobflow.ai"}
                      </span>
                    </div>
                  </div>

                  {/* 30-Day Access Pass Card inside Dropdown */}
                  <div className="p-2.5 rounded-xl bg-cream/70 border border-line/70 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-ink">
                        <ShieldCheck className="w-3.5 h-3.5 text-accent" />
                        <span>30-Day Access Pass</span>
                      </div>
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-pill">
                        <Clock className="w-2.5 h-2.5" /> {accessDays}d remaining
                      </span>
                    </div>
                    <p className="text-[11px] text-body leading-snug">
                      Authorized with active JobFlow access code for this browser profile.
                    </p>
                  </div>

                  {/* Dropdown Menu Actions */}
                  <div className="pt-1 border-t border-line">
                    <button
                      type="button"
                      onClick={handleRevokeAccess}
                      className="w-full flex items-center gap-2 px-2.5 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-lg transition-colors text-left cursor-pointer"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Reset Access Pass</span>
                    </button>
                  </div>
                </div>
              )}
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
