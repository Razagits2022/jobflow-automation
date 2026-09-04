import React from "react";
import { Container } from "@/components/ui/Container";
import { ClipboardList, EyeOff, Copy, LineChart } from "lucide-react";

const PROBLEMS = [
  {
    icon: ClipboardList,
    label: "Endless form filling",
    body: "The same fields, retyped on every site.",
  },
  {
    icon: EyeOff,
    label: "Missed postings",
    body: "Good roles close before you get to them.",
  },
  {
    icon: Copy,
    label: "Copy and paste fatigue",
    body: "Hours lost moving the same answers around.",
  },
  {
    icon: LineChart,
    label: "No tracking",
    body: "No record of where you applied or what happened.",
  },
];

export function ProblemGrid() {
  return (
    <section className="py-16 sm:py-24">
      <Container>
        {/* Two-Column Header on Desktop */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 sm:gap-10 items-end mb-12 sm:mb-16 border-b border-line pb-10">
          <div className="md:col-span-7 text-left">
            <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[42px] text-ink leading-tight tracking-tight">
              Job hunting is stuck in manual mode
            </h2>
          </div>
          <div className="md:col-span-5 text-left md:text-right">
            <p className="text-sm sm:text-base text-body leading-relaxed max-w-md md:ml-auto">
              Every posting means the same forms, the same copy and paste, the same wasted evenings. JobFlow removes the manual work completely.
            </p>
          </div>
        </div>

        {/* 2 by 2 Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 sm:gap-10">
          {PROBLEMS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.label}
                className="flex items-start gap-4 p-5 sm:p-6 rounded-card border border-line bg-canvas hover:bg-cream/40 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-accent-soft text-accent flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-5 h-5 stroke-[2.2]" />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-ink mb-1">
                    {item.label}
                  </h3>
                  <p className="text-sm sm:text-base text-body">
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
