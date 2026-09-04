"use client";

import React, { useState } from "react";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { WaveDecor } from "./WaveDecor";

type TabKey = "pipeline" | "coverage" | "reliability";

const TABS: { id: TabKey; label: string }[] = [
  { id: "pipeline", label: "Pipeline" },
  { id: "coverage", label: "ATS coverage" },
  { id: "reliability", label: "Reliability" },
];

const TAB_CONTENT: Record<
  TabKey,
  {
    title: string;
    description: string;
    badges: string[];
  }
> = {
  pipeline: {
    title: "Built to run on its own",
    description:
      "From URL extraction to form filling, file uploads, and final submission, the entire process runs without interruption.",
    badges: [
      "Runs fully unattended",
      "Screenshot proof per run",
      "Never applies twice",
    ],
  },
  coverage: {
    title: "Full portal compatibility",
    description:
      "Native support for Workday, Greenhouse, Lever, iCIMS, plus automatic fallback parsing for custom career portals.",
    badges: [
      "Auto-detects custom dropdowns",
      "Uploads tailored PDF resumes",
      "Handles multi-step applications",
    ],
  },
  reliability: {
    title: "Verified application delivery",
    description:
      "Every run confirms successful delivery on the employer portal and stores a visual confirmation timestamp.",
    badges: [
      "Anti-duplicate protection",
      "Instant submission proof",
      "Real-time status tracking",
    ],
  },
};

export function DarkCTASection() {
  const [activeTab, setActiveTab] = useState<TabKey>("pipeline");
  const content = TAB_CONTENT[activeTab];

  return (
    <section
      id="pricing"
      className="relative bg-navy py-20 sm:py-28 overflow-hidden text-white scroll-mt-20"
    >
      {/* Background Subtle Wave Lines */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <WaveDecor
          className="absolute -bottom-24 -left-20 w-[800px] h-[500px]"
          color="#F2661F"
          opacity={0.16}
        />
      </div>

      <Container className="relative z-10">
        {/* Two-Column Header */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 sm:gap-10 items-end mb-12 sm:mb-16 border-b border-line-dark pb-10">
          <div className="md:col-span-7 text-left">
            <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[44px] text-white leading-tight tracking-tight">
              Runs unattended, start to finish
            </h2>
          </div>
          <div className="md:col-span-5 text-left md:text-right">
            <p className="text-sm sm:text-base text-gray-300 leading-relaxed max-w-md md:ml-auto">
              No approvals, no babysitting. JobFlow applies in the background and records every result, so most of your applications land while you do nothing.
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 sm:gap-3 mb-8 border-b border-line-dark pb-4 overflow-x-auto">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-2 rounded-pill text-xs sm:text-sm font-semibold transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                  isActive
                    ? "bg-accent text-white shadow-sm"
                    : "text-gray-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Wide Card inside dark section */}
        <div className="rounded-card bg-navy-card border border-line-dark p-8 sm:p-12 text-left">
          <div className="max-w-2xl">
            <h3 className="font-display font-extrabold text-2xl sm:text-3xl text-white mb-3">
              {content.title}
            </h3>
            <p className="text-sm sm:text-base text-gray-300 mb-8 leading-relaxed">
              {content.description}
            </p>
          </div>

          {/* Row of Badges */}
          <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-line-dark mb-10">
            {content.badges.map((badge) => (
              <div
                key={badge}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-white/5 border border-line-dark text-xs sm:text-sm font-medium text-white"
              >
                <span className="w-2 h-2 rounded-full bg-accent" aria-hidden="true" />
                <span>{badge}</span>
              </div>
            ))}
          </div>

          {/* Action CTA */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Button
              href="/subscribe"
              variant="primary"
              size="lg"
              className="w-full sm:w-auto"
            >
              Start applying with JobFlow
            </Button>
            <span className="text-xs sm:text-sm text-gray-400">
              No credit card required. Free tier included.
            </span>
          </div>
        </div>
      </Container>
    </section>
  );
}
