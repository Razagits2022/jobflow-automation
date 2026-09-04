import React from "react";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import {
  Link2,
  ScanLine,
  UserCheck,
  Send,
  FileText,
  FormInput,
  Building2,
  Layers,
  Leaf,
  Briefcase,
} from "lucide-react";

const STEPS = [
  {
    icon: Link2,
    label: "Reads the posting",
    body: "Give it a job URL and it opens the page.",
  },
  {
    icon: ScanLine,
    label: "Understands the form",
    body: "Detects every field, type, and required answer.",
  },
  {
    icon: UserCheck,
    label: "Maps your profile",
    body: "Matches your details and resume to each field.",
  },
  {
    icon: Send,
    label: "Submits automatically",
    body: "Completes and submits without you lifting a finger.",
  },
];

const CHIPS = [
  { label: "Your resume", icon: FileText, pos: "top-4 left-4" },
  { label: "Workday", icon: Briefcase, pos: "top-4 right-4" },
  { label: "Greenhouse", icon: Leaf, pos: "top-1/2 -translate-y-1/2 left-2" },
  { label: "Lever", icon: Building2, pos: "top-1/2 -translate-y-1/2 right-2" },
  { label: "iCIMS", icon: Layers, pos: "bottom-4 left-6" },
  { label: "Any form", icon: FormInput, pos: "bottom-4 right-6" },
];

export function CoverageSection() {
  return (
    <section id="features" className="py-16 sm:py-24 bg-cream/30 border-y border-line scroll-mt-20">
      <Container>
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-14 sm:mb-18">
          <p className="text-xs sm:text-sm font-semibold text-accent tracking-wide uppercase mb-2.5">
            Coverage
          </p>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[42px] text-ink leading-tight tracking-tight">
            One link. It handles the rest.
          </h2>
          <p className="mt-3.5 text-sm sm:text-base text-body">
            Paste any career link. JobFlow navigates, parses, and completes the application end-to-end.
          </p>
        </div>

        {/* Two-Column Body */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* Left: 4 Steps Stacked Vertically */}
          <div className="lg:col-span-5 space-y-6">
            {STEPS.map((step) => {
              const Icon = step.icon;
              return (
                <div key={step.label} className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-accent-soft text-accent flex items-center justify-center shrink-0 mt-0.5">
                    <Icon className="w-5 h-5 stroke-[2.2]" />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-base sm:text-lg text-ink">
                      {step.label}
                    </h3>
                    <p className="text-sm text-body mt-0.5 leading-relaxed">
                      {step.body}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: Hub Diagram */}
          <div className="lg:col-span-7">
            <div className="relative w-full min-h-[380px] sm:min-h-[420px] rounded-card bg-canvas border border-line p-6 sm:p-8 flex items-center justify-center shadow-card overflow-hidden">
              {/* Connector Lines SVG (desktop only) */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none hidden md:block"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
              >
                {/* Center to Top-Left (Your resume) */}
                <path d="M 50% 50% L 20% 18%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
                {/* Center to Top-Right (Workday) */}
                <path d="M 50% 50% L 80% 18%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
                {/* Center to Mid-Left (Greenhouse) */}
                <path d="M 50% 50% L 16% 50%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
                {/* Center to Mid-Right (Lever) */}
                <path d="M 50% 50% L 84% 50%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
                {/* Center to Bottom-Left (iCIMS) */}
                <path d="M 50% 50% L 22% 82%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
                {/* Center to Bottom-Right (Any form) */}
                <path d="M 50% 50% L 78% 82%" stroke="#ECEBE8" strokeWidth="1.5" strokeDasharray="4 4" />
              </svg>

              {/* Desktop Absolute Chips */}
              <div className="hidden md:block absolute inset-0 pointer-events-none p-6">
                {CHIPS.map((chip) => {
                  const Icon = chip.icon;
                  return (
                    <div
                      key={chip.label}
                      className={`absolute ${chip.pos} inline-flex items-center gap-2 px-3.5 py-2 rounded-pill bg-canvas border border-line text-xs font-semibold text-ink shadow-soft pointer-events-auto`}
                    >
                      <Icon className="w-3.5 h-3.5 text-accent" />
                      <span>{chip.label}</span>
                    </div>
                  );
                })}
              </div>

              {/* Centered Node: JobFlow */}
              <div className="relative z-10 p-6 sm:p-8 rounded-2xl bg-canvas border-2 border-accent/30 shadow-lg text-center flex flex-col items-center">
                <Logo />
                <span className="mt-2 text-[11px] font-semibold text-muted tracking-wide uppercase">
                  Central Automation Engine
                </span>
              </div>

              {/* Mobile Fallback: Chips wrapped underneath node */}
              <div className="md:hidden mt-6 flex flex-wrap justify-center gap-2.5 w-full pt-4 border-t border-line">
                {CHIPS.map((chip) => {
                  const Icon = chip.icon;
                  return (
                    <div
                      key={chip.label}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-canvas border border-line text-xs font-medium text-ink shadow-2xs"
                    >
                      <Icon className="w-3.5 h-3.5 text-accent" />
                      <span>{chip.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
