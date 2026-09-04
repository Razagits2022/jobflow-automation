import React from "react";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { WaveDecor } from "./WaveDecor";

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-20 sm:pt-28 pb-16 sm:pb-24 text-center">
      {/* Wave lines positioned absolutely toward the right and edges */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <WaveDecor
          className="absolute -top-12 -right-32 w-[900px] h-[550px] opacity-75"
          color="#F2661F"
          opacity={0.32}
        />
      </div>

      <Container className="relative z-10 flex flex-col items-center">
        {/* Two-line Headline in Manrope 800 */}
        <h1 className="font-display font-extrabold text-[38px] sm:text-[50px] md:text-[58px] lg:text-[64px] text-ink leading-[1.08] tracking-[-0.03em] max-w-4xl mx-auto">
          Apply to every job automatically,
          <br className="hidden sm:inline" /> completely hands-free.
        </h1>

        {/* Muted Subtext Line */}
        <p className="mt-6 text-base sm:text-lg text-body max-w-[560px] mx-auto leading-relaxed">
          JobFlow reads each posting, fills the application, and submits it for you. You add a link, it does the rest.
        </p>

        {/* Two Centered CTAs */}
        <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 w-full sm:w-auto">
          <Button
            href="/subscribe"
            variant="primary"
            size="lg"
            className="w-full sm:w-auto shadow-sm"
          >
            Start free
          </Button>
          <Button
            href="#how-it-works"
            variant="outline"
            size="lg"
            className="w-full sm:w-auto"
          >
            See how it works
          </Button>
        </div>
      </Container>
    </section>
  );
}
