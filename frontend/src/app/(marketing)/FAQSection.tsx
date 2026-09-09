"use client";

import React, { useState } from "react";
import { Container } from "@/components/ui/Container";
import { ChevronDown, HelpCircle } from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
}

const FAQS: FAQItem[] = [
  {
    question: "How does JobFlow automatically fill applications?",
    answer:
      "JobFlow analyzes the destination career page, detects every form field (text inputs, dropdowns, radio buttons, file uploads), accurately matches your candidate profile data to each field requirement, and uploads your tailored resume PDF automatically.",
  },
  {
    question: "Which job portals and ATS platforms are supported?",
    answer:
      "JobFlow has native intelligence for major enterprise ATS platforms including Workday, Greenhouse, Lever, iCIMS, Form.io, and smart fallback parsing for custom proprietary employer career portals.",
  },
  {
    question: "How do I know my application was actually submitted?",
    answer:
      "Every submission verifies the employer confirmation screen and captures an authenticated screenshot proof with a verification timestamp, stored directly in your runs dashboard so you always have visual proof.",
  },
  {
    question: "Is my personal data and resume secure?",
    answer:
      "Yes, completely. Your profile and resumes are encrypted and exclusively used to fill out the specific job applications you choose. We never share, sell, or monetize candidate data.",
  },
  {
    question: "Can JobFlow handle multi-step application wizards?",
    answer:
      "Yes. JobFlow automatically advances through multi-step application forms, handles 'Next / Save & Continue' transitions, fills required screening questions from your profile facts, and completes final submission.",
  },
  {
    question: "Do I have to keep my computer open while it applies?",
    answer:
      "No! JobFlow's cloud automation workers process applications asynchronously in the background. You can paste your job links, shut your laptop, and check your dashboard anytime for submission proof.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const toggleFAQ = (index: number) => {
    setOpenIndex((prev) => (prev === index ? null : index));
  };

  return (
    <section id="faq" className="py-16 sm:py-24 bg-canvas scroll-mt-20 border-t border-line">
      <Container>
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent-soft text-accent text-xs font-semibold mb-3">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Got Questions?</span>
          </div>
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl lg:text-[42px] text-ink leading-tight tracking-tight">
            Frequently Asked Questions
          </h2>
          <p className="mt-3.5 text-sm sm:text-base text-body">
            Everything you need to know about how JobFlow automates your job search.
          </p>
        </div>

        {/* Accordion List */}
        <div className="max-w-3xl mx-auto space-y-4">
          {FAQS.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={faq.question}
                className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
                  isOpen
                    ? "border-accent/50 bg-accent-soft/20 shadow-xs"
                    : "border-line bg-canvas hover:border-line/90"
                }`}
              >
                <button
                  type="button"
                  onClick={() => toggleFAQ(idx)}
                  className="w-full text-left px-5 sm:px-6 py-4 sm:py-5 flex items-center justify-between gap-4 cursor-pointer"
                  aria-expanded={isOpen}
                >
                  <span className="font-display font-bold text-base sm:text-lg text-ink">
                    {faq.question}
                  </span>
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-transform duration-200 ${
                      isOpen
                        ? "rotate-180 bg-accent text-white"
                        : "bg-line/40 text-muted"
                    }`}
                  >
                    <ChevronDown className="w-4 h-4" />
                  </div>
                </button>

                {isOpen && (
                  <div className="px-5 sm:px-6 pb-5 sm:pb-6 pt-1 text-sm sm:text-base text-body leading-relaxed animate-in fade-in duration-150">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
