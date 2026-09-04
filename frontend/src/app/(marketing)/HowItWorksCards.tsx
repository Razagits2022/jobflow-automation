import React from "react";
import { Container } from "@/components/ui/Container";
import { FileSearch, PencilLine, BadgeCheck } from "lucide-react";

const STEPS = [
  {
    icon: FileSearch,
    title: "Reads any posting",
    body: "Pulls the role, requirements, and screening questions straight from the job page.",
  },
  {
    icon: PencilLine,
    title: "Fills every field",
    body: "Maps your profile and resume onto the form, including custom dropdowns and file uploads.",
  },
  {
    icon: BadgeCheck,
    title: "Submits with proof",
    body: "Sends the application and saves a screenshot of the confirmation for every run.",
  },
];

export function HowItWorksCards() {
  return (
    <section id="how-it-works" className="py-16 sm:py-24 scroll-mt-20">
      <Container>
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <p className="text-xs sm:text-sm font-semibold text-accent tracking-wide uppercase mb-2.5">
            How it works
          </p>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[42px] text-ink leading-tight tracking-tight">
            Never fill another application form
          </h2>
          <p className="mt-3.5 text-sm sm:text-base text-body">
            From job posting to verified submission in minutes, without touching a single field.
          </p>
        </div>

        {/* 3 Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {STEPS.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.title}
                className="bg-canvas border border-line rounded-card shadow-card p-7 sm:p-8 flex flex-col items-start text-left transition-all duration-200 hover:-translate-y-1"
              >
                {/* Rounded square with soft peach background */}
                <div className="w-12 h-12 rounded-xl bg-accent-soft text-accent flex items-center justify-center mb-6">
                  <Icon className="w-6 h-6 stroke-[2.2]" />
                </div>

                <h3 className="font-display font-bold text-xl text-ink mb-2.5">
                  {step.title}
                </h3>
                <p className="text-sm sm:text-base text-body leading-relaxed">
                  {step.body}
                </p>
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
