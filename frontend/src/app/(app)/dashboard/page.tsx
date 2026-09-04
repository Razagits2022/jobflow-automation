"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useAppStore } from "@/lib/store";
import { Card, Button, Stat, StatusBadge } from "@/components/ui";
import { formatDistanceToNow } from "date-fns";
import {
  Send,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  ArrowRight,
  Upload,
  ExternalLink,
  RotateCcw,
} from "lucide-react";

function getDomain(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return "Job Portal";
  }
}

export default function DashboardPage() {
  const runs = useAppStore((state) => state.runs);
  const profile = useAppStore((state) => state.profile);
  const reset = useAppStore((state) => state.reset);
  const loadRuns = useAppStore((state) => state.loadRuns);
  const loadProfile = useAppStore((state) => state.loadProfile);

  useEffect(() => {
    loadRuns();
    loadProfile();

    const timer = setInterval(() => {
      loadRuns();
    }, 5000);

    return () => clearInterval(timer);
  }, [loadRuns, loadProfile]);

  const totalRuns = runs.length;
  const submittedCount = runs.filter((r) => r.status === "submitted").length;
  const failedCount = runs.filter(
    (r) => r.status === "failed" || r.status === "failed_validation"
  ).length;
  const blockedCount = runs.filter((r) => r.status === "failed_captcha").length;

  const recentRuns = runs.slice(0, 5);

  return (
    <div className="max-w-4xl mx-auto space-y-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
            Overview
          </h1>
          <p className="mt-1 text-sm sm:text-base text-body">
            Monitor real-time progress and application delivery.
          </p>
        </div>

        <Button href="/apply" variant="primary" size="md" className="shadow-sm">
          <span>Apply to more jobs</span>
          <ArrowRight className="w-4 h-4 ml-1" />
        </Button>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-5">
        <Stat
          label="Total applications"
          value={totalRuns}
          subtext="Processed in queue"
          icon={<Send className="w-4 h-4 text-muted" />}
        />
        <Stat
          label="Submitted"
          value={submittedCount}
          subtext="Confirmed by employer"
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
        />
        <Stat
          label="Issues"
          value={failedCount}
          subtext="Form & portal errors"
          icon={<XCircle className="w-4 h-4 text-red-600" />}
        />
        <Stat
          label="Blocked (CAPTCHA)"
          value={blockedCount}
          subtext="Shield challenges"
          icon={<ShieldAlert className="w-4 h-4 text-amber-600" />}
        />
      </div>

      {/* Primary CTA Card */}
      <Card className="bg-gradient-to-r from-cream/60 via-canvas to-accent-soft/30 border-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 p-6 sm:p-8">
        <div className="space-y-1 max-w-xl text-left">
          <span className="text-xs font-bold text-accent uppercase tracking-wider block">
            Autonomous Pipeline
          </span>
          <h2 className="font-display font-extrabold text-xl sm:text-2xl text-ink">
            Have more job postings to apply to?
          </h2>
          <p className="text-xs sm:text-sm text-body">
            Paste career links or import a CSV list. JobFlow navigates and submits each one hands-free.
          </p>
        </div>

        <Button href="/apply" variant="primary" size="lg" className="shrink-0 shadow-sm">
          Launch applications
        </Button>
      </Card>

      {/* Recent Applications Section */}
      <div className="space-y-4 text-left">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-lg sm:text-xl text-ink">
            Recent applications
          </h2>
          {runs.length > 0 && (
            <Link
              href="/runs"
              className="text-xs sm:text-sm font-semibold text-accent hover:underline flex items-center gap-1"
            >
              <span>View all ({runs.length})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {runs.length === 0 ? (
          /* Empty State */
          <Card className="text-center py-12 space-y-4">
            <div className="w-12 h-12 rounded-xl bg-cream border border-line text-muted flex items-center justify-center mx-auto">
              {!profile ? <Upload className="w-6 h-6" /> : <Send className="w-6 h-6" />}
            </div>
            <div>
              <h3 className="font-display font-bold text-lg text-ink">
                {!profile ? "Get started by uploading your resume" : "Ready to apply"}
              </h3>
              <p className="text-xs sm:text-sm text-muted max-w-sm mx-auto mt-1">
                {!profile
                  ? "We analyze your resume to automatically generate the profile data used on application forms."
                  : "Queue your first batch of job URLs to let JobFlow apply on autopilot."}
              </p>
            </div>
            <Button
              href={!profile ? "/onboarding" : "/apply"}
              variant="primary"
              size="md"
              className="shadow-sm"
            >
              {!profile ? "Upload resume" : "Add job links"}
            </Button>
          </Card>
        ) : (
          /* Recent Runs List */
          <div className="divide-y divide-line rounded-card border border-line bg-canvas overflow-hidden shadow-card">
            {recentRuns.map((run) => {
              const domain = getDomain(run.url);
              let timeAgo = "Just now";
              try {
                timeAgo = formatDistanceToNow(new Date(run.createdAt), {
                  addSuffix: true,
                });
              } catch {
                timeAgo = "recently";
              }

              return (
                <div
                  key={run.id}
                  className="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-cream/30 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-0.5">
                      <span className="font-display font-bold text-sm text-ink truncate">
                        {domain}
                      </span>
                      <StatusBadge status={run.status} />
                    </div>
                    <p className="text-xs text-muted font-mono truncate max-w-sm sm:max-w-lg">
                      {run.url}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-muted font-normal hidden sm:inline-block">
                      {timeAgo}
                    </span>
                    <a
                      href={
                        run.url.startsWith("http://") || run.url.startsWith("https://")
                          ? run.url
                          : `https://${run.url}`
                      }
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 text-muted hover:text-ink rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      title="Open job link"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Developer Reset Demo Button */}
      <div className="pt-6 border-t border-line text-center">
        <button
          type="button"
          onClick={() => reset()}
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink font-medium px-3 py-1.5 rounded-pill hover:bg-cream transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset client session</span>
        </button>
      </div>
    </div>
  );
}
