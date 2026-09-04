"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { Card, Button, Field } from "@/components/ui";
import { Check, ShieldCheck, Lock } from "lucide-react";

const FEATURES = [
  "Unlimited job applications",
  "Runs fully unattended",
  "Screenshot proof for every application",
  "Never applies to the same job twice",
];

export function SubscribePage() {
  const router = useRouter();
  const subscribe = useAppStore((state) => state.subscribe);
  const [nameOnCard, setNameOnCard] = useState("Raza Haider");
  const [cardNumber, setCardNumber] = useState("4242 •••• •••• 4242");
  const [expiry, setExpiry] = useState("12/28");
  const [cvc, setCvc] = useState("888");

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    subscribe();
    router.push("/onboarding");
  };

  return (
    <div className="w-full max-w-lg mx-auto text-center space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
          Start applying on autopilot
        </h1>
        <p className="mt-2 text-sm sm:text-base text-body">
          One plan. Cancel anytime.
        </p>
      </div>

      {/* Pricing Card */}
      <Card className="text-left space-y-6">
        <div className="flex items-baseline justify-between border-b border-line pb-6">
          <div>
            <span className="text-xs font-bold text-accent uppercase tracking-wider block">
              Pro Plan
            </span>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className="font-display font-extrabold text-4xl sm:text-5xl text-ink">
                $79
              </span>
              <span className="text-sm font-medium text-muted">/month</span>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-pill">
            <ShieldCheck className="w-3.5 h-3.5" /> 7-day guarantee
          </span>
        </div>

        {/* Feature List */}
        <ul className="space-y-3 text-sm text-body">
          {FEATURES.map((feature) => (
            <li key={feature} className="flex items-center gap-3">
              <div className="w-5 h-5 rounded-full bg-accent-soft text-accent flex items-center justify-center shrink-0">
                <Check className="w-3.5 h-3.5 stroke-[2.8]" />
              </div>
              <span>{feature}</span>
            </li>
          ))}
        </ul>

        {/* Fake Card Form */}
        <form onSubmit={handleSubscribe} className="pt-4 border-t border-line space-y-4">
          <div className="flex items-center justify-between text-xs text-muted mb-1">
            <span className="font-semibold text-ink">Payment details</span>
            <span className="flex items-center gap-1 text-[11px]">
              <Lock className="w-3 h-3 text-emerald-600" /> End-to-end encrypted
            </span>
          </div>

          <Field label="Name on card">
            <input
              type="text"
              value={nameOnCard}
              onChange={(e) => setNameOnCard(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
              required
            />
          </Field>

          <Field label="Card number">
            <input
              type="text"
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono"
              required
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Expiry date">
              <input
                type="text"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono text-center"
                required
              />
            </Field>

            <Field label="CVC">
              <input
                type="text"
                value={cvc}
                onChange={(e) => setCvc(e.target.value)}
                className="w-full px-3.5 py-2 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono text-center"
                required
              />
            </Field>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full mt-4 font-bold shadow-sm"
          >
            Subscribe for $79
          </Button>

          <p className="text-center text-xs text-muted pt-1">
            Demo only. No real charge is made.
          </p>
        </form>
      </Card>
    </div>
  );
}

export default SubscribePage;
