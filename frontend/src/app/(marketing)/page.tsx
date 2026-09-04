import React from "react";
import { Hero } from "./Hero";
import { StatsBand } from "./StatsBand";
import { HowItWorksCards } from "./HowItWorksCards";
import { ProblemGrid } from "./ProblemGrid";
import { CoverageSection } from "./CoverageSection";
import { DarkCTASection } from "./DarkCTASection";

export default function MarketingPage() {
  return (
    <>
      {/* 1. Hero */}
      <Hero />

      {/* 2. StatsBand */}
      <StatsBand />

      {/* 3. HowItWorksCards */}
      <HowItWorksCards />

      {/* 4. ProblemGrid */}
      <ProblemGrid />

      {/* 5. CoverageSection */}
      <CoverageSection />

      {/* 6. DarkCTASection */}
      <DarkCTASection />
    </>
  );
}
