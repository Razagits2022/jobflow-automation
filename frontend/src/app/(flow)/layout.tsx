import React from "react";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export default function FlowLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full bg-canvas flex flex-col justify-between">
      {/* Minimal Header with Logo only */}
      <header className="border-b border-line py-5">
        <Container className="flex items-center justify-center">
          <Logo />
        </Container>
      </header>

      {/* Centered Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center py-12 sm:py-16">
        <Container size="sm" className="w-full">
          {children}
        </Container>
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-line py-6 text-center text-xs text-muted">
        <Container size="sm">
          JobFlow Security &amp; Data Privacy Guarantee. No passwords stored.
        </Container>
      </footer>
    </div>
  );
}
