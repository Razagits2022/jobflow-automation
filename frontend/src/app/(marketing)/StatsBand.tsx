import React from "react";
import { Container } from "@/components/ui/Container";

/**
 * Placeholder stats to confirm with production metrics later.
 */
const STATS = [
  { value: "50K+", label: "Applications submitted" },
  { value: "7 / 10", label: "Auto-apply success" },
  { value: "4+", label: "ATS platforms" },
  { value: "0", label: "Manual clicks" },
];

export function StatsBand() {
  return (
    <section className="py-6 sm:py-10">
      <Container>
        <div className="bg-canvas border border-line rounded-card shadow-soft px-6 py-8 sm:py-10 text-center">
          {/* Eyebrow */}
          <p className="text-xs sm:text-sm font-medium text-muted tracking-wide mb-6 sm:mb-8">
            By the numbers
          </p>

          {/* 4 Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-4 divide-y md:divide-y-0 md:divide-x divide-line">
            {STATS.map((stat, idx) => (
              <div
                key={stat.label}
                className={`flex flex-col items-center justify-center ${
                  idx > 1 ? "pt-6 md:pt-0" : ""
                } ${idx % 2 === 1 ? "pl-2" : "pr-2"} md:px-4`}
              >
                <span className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
                  {stat.value}
                </span>
                <span className="mt-2 text-xs sm:text-sm text-muted font-normal">
                  {stat.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
