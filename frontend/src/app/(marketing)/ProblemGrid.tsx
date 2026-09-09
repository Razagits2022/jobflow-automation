import React from "react";
import { Container } from "@/components/ui/Container";
import { Zap, Target, Camera, ShieldCheck } from "lucide-react";

const WHY_CHOOSE_JOBFLOW = [
  {
    icon: Zap,
    label: "10x Application Speed",
    body: "Transform 25 minutes of painful manual typing into a 15-second link paste. Apply to more high-quality roles in less time.",
  },
  {
    icon: Target,
    label: "Native ATS Intelligence",
    body: "Built specifically to navigate complex Workday portals, Greenhouse workflows, and Lever forms without breaking or getting stuck.",
  },
  {
    icon: Camera,
    label: "Verified Screenshot Proof",
    body: "Every single application saves an official confirmation screenshot and timestamp so you always know your application was received.",
  },
  {
    icon: ShieldCheck,
    label: "Zero Duplicate Applications",
    body: "JobFlow automatically tracks your history across companies and URLs to ensure you never accidentally apply to the same role twice.",
  },
];

export function ProblemGrid() {
  return (
    <section id="why-jobflow" className="py-16 sm:py-24 bg-canvas scroll-mt-20">
      <Container>
        {/* Two-Column Header on Desktop */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 sm:gap-10 items-end mb-12 sm:mb-16 pb-6">
          <div className="md:col-span-7 text-left">
            <p className="text-xs sm:text-sm font-semibold text-accent tracking-wide uppercase mb-2.5">
              Why Choose JobFlow
            </p>
            <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[42px] text-ink leading-tight tracking-tight">
              Stop wasting evenings on repetitive job forms
            </h2>
          </div>
          <div className="md:col-span-5 text-left md:text-right">
            <p className="text-sm sm:text-base text-body leading-relaxed max-w-md md:ml-auto">
              Traditional job hunting means retyping the exact same contact details, education, and resume answers on every site. JobFlow automates the entire loop hands-free.
            </p>
          </div>
        </div>

        {/* 2 by 2 Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 sm:gap-8">
          {WHY_CHOOSE_JOBFLOW.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-start gap-4 p-6 sm:p-7 rounded-2xl border border-line bg-canvas hover:border-accent/40 hover:shadow-soft transition-all duration-200"
              >
                <div className="w-11 h-11 rounded-xl bg-accent-soft text-accent flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-5 h-5 stroke-[2.2]" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-ink mb-1.5">
                    {item.label}
                  </h3>
                  <p className="text-sm text-body leading-relaxed">
                    {item.body}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
