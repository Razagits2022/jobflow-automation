"use client";

import React, { useState, useEffect } from "react";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { WaveDecor } from "./WaveDecor";
import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Globe,
  FileText,
  Send,
  ShieldCheck,
  Zap,
} from "lucide-react";

const PIPELINE_STAGES = [
  {
    step: 1,
    label: "Scanning Posting",
    detail: "Extracted 14 ATS fields from Workday",
    icon: Globe,
    color: "text-blue-500",
    bg: "bg-blue-50",
  },
  {
    step: 2,
    label: "Auto-Filling Form",
    detail: "Mapped profile, custom dropdowns & resume PDF",
    icon: FileText,
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
  {
    step: 3,
    label: "Verified & Submitted",
    detail: "Confirmation proof captured #49281 • Zero manual effort",
    icon: CheckCircle2,
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
];

export function Hero() {
  const [activeStage, setActiveStage] = useState(0);

  // Auto-cycle through pipeline stages every 3 seconds for dynamic demo animation
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % PIPELINE_STAGES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative overflow-hidden pt-16 sm:pt-24 pb-16 sm:pb-24 text-center bg-canvas">
      {/* Ambient Pulsing Glow in Background */}
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] sm:w-[750px] h-[350px] bg-gradient-to-b from-accent/10 via-amber-200/15 to-transparent blur-3xl pointer-events-none rounded-full animate-pulse-glow"
        aria-hidden="true"
      />

      {/* Wave lines positioned toward the right and edges */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <WaveDecor
          className="absolute -top-12 -right-32 w-[900px] h-[550px] opacity-75 animate-pulse-glow"
          color="#F2661F"
          opacity={0.3}
        />
      </div>

      <Container className="relative z-10 flex flex-col items-center">
        {/* Floating Top Pill Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-accent/25 bg-accent-soft/70 text-xs font-semibold text-accent shadow-xs mb-6 sm:mb-8 transition-all hover:scale-105 cursor-default">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
          </span>
          <span>Autopilot for Job Applications</span>
          <Sparkles className="w-3.5 h-3.5 text-accent animate-pulse" />
        </div>

        {/* Two-line Headline in Manrope 800 */}
        <h1 className="font-display font-extrabold text-[38px] sm:text-[50px] md:text-[58px] lg:text-[66px] text-ink leading-[1.06] tracking-[-0.03em] max-w-4xl mx-auto">
          Apply to every job automatically,
          <br className="hidden sm:inline" /> completely{" "}
          <span className="bg-gradient-to-r from-accent via-[#E55512] to-amber-500 bg-clip-text text-transparent">
            hands-free.
          </span>
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
            className="w-full sm:w-auto shadow-md group inline-flex items-center justify-center gap-2 transition-transform hover:-translate-y-0.5"
          >
            <span>Start free</span>
            <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
          </Button>
          <Button
            href="#how-it-works"
            variant="outline"
            size="lg"
            className="w-full sm:w-auto hover:bg-cream/40 transition-colors"
          >
            See how it works
          </Button>
        </div>

        {/* Interactive Live Demo Preview Card */}
        <div className="mt-14 sm:mt-18 w-full max-w-3xl relative">
          {/* Floating Chip Left */}
          <div className="hidden md:flex absolute -left-6 top-8 z-20 items-center gap-2 px-3.5 py-2 rounded-full bg-canvas/95 backdrop-blur-md border border-line shadow-soft text-xs font-semibold text-ink animate-float-slow">
            <Zap className="w-4 h-4 text-accent" />
            <span>Workday, Lever & Greenhouse</span>
          </div>

          {/* Floating Chip Right */}
          <div className="hidden md:flex absolute -right-6 bottom-8 z-20 items-center gap-2 px-3.5 py-2 rounded-full bg-canvas/95 backdrop-blur-md border border-line shadow-soft text-xs font-semibold text-ink animate-float-reverse">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Verified Delivery Proof</span>
          </div>

          {/* Browser Container */}
          <div className="rounded-2xl border border-line bg-canvas shadow-card overflow-hidden text-left transition-all">
            {/* Top Mock Window Bar */}
            <div className="bg-canvas border-b border-line px-4 py-3 flex items-center gap-2.5">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-rose-400" />
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <div className="w-3 h-3 rounded-full bg-emerald-400" />
              </div>
              <div className="flex-1 mx-2 sm:mx-6">
                <div className="bg-cream/50 border border-line rounded-lg px-3 py-1 text-xs text-muted font-mono truncate flex items-center justify-between">
                  <span className="truncate">https://jobs.company.com/careers/senior-engineer/apply</span>
                  <span className="hidden sm:inline-block text-[10px] text-accent font-semibold ml-2 shrink-0">
                    ● AUTO RUNNING
                  </span>
                </div>
              </div>
            </div>

            {/* Inner Live Automation Pipeline */}
            <div className="p-5 sm:p-7">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="font-display font-bold text-sm sm:text-base text-ink">
                    Live Job Application Pipeline
                  </h3>
                  <p className="text-xs text-muted mt-0.5">
                    JobFlow engine processing candidate profile in background
                  </p>
                </div>
                <span className="text-xs font-semibold text-accent bg-accent-soft px-2.5 py-1 rounded-md">
                  Step {activeStage + 1} of 3
                </span>
              </div>

              {/* Progress Steps Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
                {PIPELINE_STAGES.map((stage, idx) => {
                  const Icon = stage.icon;
                  const isActive = idx === activeStage;
                  const isCompleted = idx < activeStage;

                  return (
                    <div
                      key={stage.label}
                      onClick={() => setActiveStage(idx)}
                      className={`cursor-pointer p-3.5 rounded-xl border transition-all duration-300 ${
                        isActive
                          ? "border-accent bg-accent-soft/30 shadow-xs scale-[1.02]"
                          : isCompleted
                          ? "border-emerald-200 bg-emerald-50/30"
                          : "border-line bg-canvas hover:border-line/80"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 mb-2">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                            isActive
                              ? "bg-accent text-white"
                              : isCompleted
                              ? "bg-emerald-500 text-white"
                              : "bg-line/60 text-muted"
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p
                            className={`text-xs font-bold truncate ${
                              isActive ? "text-accent" : isCompleted ? "text-emerald-700" : "text-ink"
                            }`}
                          >
                            {stage.label}
                          </p>
                        </div>
                      </div>
                      <p className="text-[11px] text-muted leading-tight line-clamp-2">
                        {stage.detail}
                      </p>
                    </div>
                  );
                })}
              </div>

              {/* Active Pipeline Status Banner */}
              <div className="mt-5 p-3.5 rounded-xl bg-canvas border border-line flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-2 h-2 rounded-full bg-accent animate-ping" />
                  <span className="font-mono text-xs text-body truncate">
                    Current task: <strong className="text-ink">{PIPELINE_STAGES[activeStage].label}</strong> — {PIPELINE_STAGES[activeStage].detail}
                  </span>
                </div>
                <span className="hidden sm:inline-block text-[11px] font-semibold text-muted shrink-0 ml-3">
                  100% Automated
                </span>
              </div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
