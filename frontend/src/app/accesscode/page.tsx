"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { grantAccess, hasValidAccess, getRemainingDays } from "@/lib/access-code";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { ShieldCheck, Lock, ArrowRight, AlertCircle, Sparkles, CheckCircle2, Clock, Eye, EyeOff } from "lucide-react";

function AccessCodeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("returnUrl") || "/dashboard";

  const [code, setCode] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [alreadyUnlockedDays, setAlreadyUnlockedDays] = useState<number | null>(null);

  useEffect(() => {
    // If user already has valid access, show active state or auto-redirect
    if (hasValidAccess()) {
      const days = getRemainingDays();
      setAlreadyUnlockedDays(days);
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    // Simulate brief smooth verification animation
    setTimeout(() => {
      const result = grantAccess(code);
      if (result.success) {
        setIsSuccess(true);
        setTimeout(() => {
          router.replace(decodeURIComponent(returnUrl));
        }, 600);
      } else {
        setError(result.error || "Invalid access code. Please check with your team.");
        setIsSubmitting(false);
      }
    }, 400);
  };

  const handleContinue = () => {
    router.replace(decodeURIComponent(returnUrl));
  };

  return (
    <div className="min-h-screen w-full bg-canvas text-ink flex flex-col justify-between items-center px-4 py-8 relative overflow-hidden selection:bg-accent selection:text-white">
      {/* Subtle Background Glow Elements */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-accent/10 rounded-full blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 right-1/4 w-[400px] h-[300px] bg-sky-500/5 rounded-full blur-3xl"
      />

      {/* Top Header */}
      <header className="w-full max-w-4xl flex items-center justify-between z-10">
        <Logo href="/accesscode" />
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-body bg-line/40 px-3 py-1.5 rounded-pill border border-line">
          <ShieldCheck className="w-3.5 h-3.5 text-accent" />
          <span>Private Deployment</span>
        </span>
      </header>

      {/* Main Card */}
      <main className="w-full max-w-md my-auto z-10">
        <div className="bg-canvas border border-line/80 shadow-2xl rounded-2xl p-6 sm:p-8 backdrop-blur-xl relative">
          {/* Security Icon Accent */}
          <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mx-auto mb-5 shadow-inner">
            {isSuccess ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-600 animate-bounce" />
            ) : alreadyUnlockedDays !== null ? (
              <Sparkles className="w-6 h-6 text-accent" />
            ) : (
              <Lock className="w-6 h-6 text-accent" />
            )}
          </div>

          <div className="text-center space-y-2 mb-6">
            <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-ink tracking-tight">
              {isSuccess
                ? "Access Granted!"
                : alreadyUnlockedDays !== null
                ? "Access Pass Active"
                : "Enter Access Code"}
            </h1>
            <p className="text-xs sm:text-sm text-body leading-relaxed">
              {isSuccess
                ? "Redirecting you to your JobFlow workspace..."
                : alreadyUnlockedDays !== null
                ? `You have an active session with ${alreadyUnlockedDays} days remaining.`
                : "This private JobFlow release requires an authorized code. Once unlocked, access is saved for 30 days."}
            </p>
          </div>

          {alreadyUnlockedDays !== null && !isSuccess ? (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 text-xs flex items-center gap-2.5">
                <Clock className="w-4 h-4 shrink-0" />
                <span>Your browser is authorized for the next {alreadyUnlockedDays} days.</span>
              </div>

              <Button
                variant="primary"
                className="w-full justify-center text-sm py-3"
                onClick={handleContinue}
              >
                <span>Continue to JobFlow</span>
                <ArrowRight className="w-4 h-4 ml-1.5" />
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="access-code"
                  className="block text-xs font-bold text-muted uppercase tracking-wider mb-2 text-left"
                >
                  Access Code
                </label>
                <div className="relative">
                  <input
                    id="access-code"
                    type={showPassword ? "text" : "password"}
                    value={code}
                    onChange={(e) => {
                      setCode(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="Enter access code..."
                    autoFocus
                    disabled={isSubmitting || isSuccess}
                    autoComplete="off"
                    autoCorrect="off"
                    spellCheck={false}
                    className="w-full bg-cream/50 border border-line text-ink placeholder:text-muted/60 rounded-xl pl-4 pr-11 py-3 text-sm font-semibold tracking-wider uppercase transition-all duration-150 focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink p-1 rounded-md transition-colors cursor-pointer"
                    aria-label={showPassword ? "Hide access code" : "Show access code"}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {error && (
                  <div className="mt-2.5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 text-xs flex items-start gap-2 animate-shake">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting || isSuccess || !code.trim()}
                className="w-full justify-center text-sm py-3 transition-all duration-150"
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Verifying Code...</span>
                  </span>
                ) : isSuccess ? (
                  <span className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Unlocked! Redirecting...</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <span>Unlock JobFlow</span>
                    <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </Button>
            </form>
          )}

          {/* 30-Day Badge & Helper Details */}
          <div className="mt-6 pt-5 border-t border-line/60 flex items-center justify-between text-[11px] text-muted">
            <span className="inline-flex items-center gap-1.5 font-medium">
              <Clock className="w-3.5 h-3.5 text-accent" />
              <span>Valid for 30 days</span>
            </span>
            <span className="font-medium">Per-profile session</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-4xl text-center text-xs text-muted py-4 z-10">
        <span>JobFlow Automation © 2026. Private Deployment.</span>
      </footer>
    </div>
  );
}

export default function AccessCodePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-canvas flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AccessCodeContent />
    </Suspense>
  );
}
