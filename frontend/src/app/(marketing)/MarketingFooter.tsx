import React from "react";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { BRAND_NAME, BRAND_TAGLINE } from "@/lib/brand";

const FOOTER_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Why JobFlow", href: "#why-jobflow" },
  { label: "Supported ATS", href: "#features" },
  { label: "FAQ", href: "#faq" },
  { label: "Contact", href: "mailto:support@jobflow.ai" },
];

export function MarketingFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer id="contact" className="bg-canvas border-t border-line py-12 sm:py-16 scroll-mt-20">
      <Container className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
        {/* Left: Logo and Tagline */}
        <div className="flex flex-col items-start gap-2">
          <Logo />
          <p className="text-xs sm:text-sm text-muted max-w-sm">
            {BRAND_TAGLINE}
          </p>
          <a
            href="mailto:support@jobflow.ai"
            className="text-xs font-semibold text-accent hover:underline mt-1 inline-flex items-center gap-1.5"
          >
            <span>support@jobflow.ai</span>
          </a>
        </div>

        {/* Right: Links and Copyright */}
        <div className="flex flex-col items-start md:items-end gap-3">
          <nav className="flex flex-wrap items-center gap-6 text-xs sm:text-sm font-medium text-body">
            {FOOTER_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="hover:text-ink transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <p className="text-xs text-muted">
            &copy; {currentYear} {BRAND_NAME}. All rights reserved.
          </p>
        </div>
      </Container>
    </footer>
  );
}
