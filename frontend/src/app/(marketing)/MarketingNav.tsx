"use client";

import React, { useState } from "react";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { Menu, X } from "lucide-react";

const NAV_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Why JobFlow", href: "#why-jobflow" },
  { label: "Supported ATS", href: "#features" },
  { label: "FAQ", href: "#faq" },
];

export function MarketingNav() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-canvas/95 backdrop-blur-md border-b border-line">
      <Container className="flex items-center justify-between h-18 sm:h-20">
        {/* Left: Logo */}
        <div className="flex items-center shrink-0">
          <Logo />
        </div>

        {/* Center: Desktop Navigation Links */}
        <nav className="hidden md:flex items-center justify-center gap-10 text-sm font-medium text-body flex-1">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="hover:text-ink transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-sm px-1 py-0.5"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-3 sm:gap-5 shrink-0">
          <Button href="/subscribe" variant="primary" size="sm" className="shadow-2xs">
            Start free
          </Button>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-body hover:text-ink outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </Container>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-canvas border-b border-line px-6 py-5 flex flex-col gap-4 animate-in fade-in duration-150">
          <nav className="flex flex-col gap-3 text-base font-medium text-body">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="py-1 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="pt-2 border-t border-line">
            <Button
              href="/subscribe"
              variant="primary"
              size="sm"
              className="w-full justify-center shadow-2xs"
            >
              Start free
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
