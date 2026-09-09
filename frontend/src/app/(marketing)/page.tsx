import React from "react";
import { Hero } from "./Hero";
import { StatsBand } from "./StatsBand";
import { HowItWorksCards } from "./HowItWorksCards";
import { ProblemGrid } from "./ProblemGrid";
import { CoverageSection } from "./CoverageSection";
import { FAQSection } from "./FAQSection";

export default function MarketingPage() {
  return (
    <>
      {/* 1. Hero */}
      <Hero />

      {/* 2. StatsBand */}
      <StatsBand />

      {/* 3. HowItWorksCards */}
      <HowItWorksCards />

      {/* 4. Why JobFlow (Problem vs Solution) */}
      <ProblemGrid />

      {/* 5. Supported Portals (Coverage) */}
      <CoverageSection />

      {/* 6. FAQ */}
      <FAQSection />
    </>
  );
}
