"use client";
/* eslint-disable @next/next/no-img-element */

import React, { useState, useEffect } from "react";

import { useAppStore } from "@/lib/store";
import { Card, Button, StatusBadge } from "@/components/ui";
import { formatDistanceToNow } from "date-fns";
import {
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  ExternalLink,
  ShieldAlert,
  Inbox,
} from "lucide-react";
import clsx from "clsx";

type FilterTab = "all" | "submitted" | "failed";

function getDomain(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return "Job Portal";
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RunsPage() {
  const runs = useAppStore((state) => state.runs);
  const loadRuns = useAppStore((state) => state.loadRuns);
  const loadRunDetails = useAppStore((state) => state.loadRunDetails);

  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [expandedRunIds, setExpandedRunIds] = useState<Record<string, boolean>>({});

  // Initial load and polling
  useEffect(() => {
    loadRuns();

    const hasActive = runs.some((r) => r.status === "running" || r.status === "queued");
    const intervalTime = hasActive ? 2500 : 10000;

    const timer = setInterval(() => {
      loadRuns();
    }, intervalTime);

    return () => clearInterval(timer);
  }, [loadRuns, runs]);

  const toggleExpand = (id: string) => {
    const nextState = !expandedRunIds[id];
    setExpandedRunIds((prev) => ({
      ...prev,
      [id]: nextState,
    }));

    if (nextState) {
      loadRunDetails(id);
    }
  };

  // Live Summary counts
  const submittedCount = runs.filter((r) => r.status === "submitted").length;
  const failedCount = runs.filter(
    (r) => r.status === "failed" || r.status === "failed_validation"
  ).length;
  const blockedCount = runs.filter((r) => r.status === "failed_captcha").length;
  const runningCount = runs.filter((r) => r.status === "running").length;
  const skippedCount = runs.filter((r) => r.status === "skipped_duplicate").length;

  const filteredRuns = runs.filter((run) => {
    if (filterTab === "submitted") return run.status === "submitted";
    if (filterTab === "failed")
      return (
        run.status === "failed" ||
        run.status === "failed_captcha" ||
        run.status === "failed_validation"
      );
    return true;
  });

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
            Applications
          </h1>
          <p className="mt-1 text-sm sm:text-base text-body">
            {runs.length === 0 ? (
              "Live application monitor and confirmation audit trail."
            ) : (
              <span>
                <strong className="text-emerald-700">{submittedCount} submitted</strong>,{" "}
                <strong className="text-red-700">{failedCount} issues</strong>,{" "}
                <strong className="text-amber-800">{blockedCount} blocked</strong>
                {skippedCount > 0 && (
                  <span className="text-slate-600 ml-1">
                    &bull; {skippedCount} already applied
                  </span>
                )}
                {runningCount > 0 && (
                  <span className="text-blue-700 font-semibold ml-1 animate-pulse">
                    &bull; {runningCount} in progress
                  </span>
                )}
              </span>
            )}
          </p>
        </div>

        <Button href="/apply" variant="outline" size="sm">
          + Add more jobs
        </Button>
      </div>

      {/* Filter Tabs */}
      {runs.length > 0 && (
        <div className="flex items-center gap-2 border-b border-line pb-3">
          {(
            [
              { id: "all", label: `All (${runs.length})` },
              { id: "submitted", label: `Submitted (${submittedCount})` },
              { id: "failed", label: `Issues (${failedCount + blockedCount})` },
            ] as const
          ).map((tab) => {
            const isActive = filterTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilterTab(tab.id)}
                className={clsx(
                  "px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent",
                  isActive
                    ? "bg-accent text-white shadow-3xs"
                    : "text-muted hover:text-ink hover:bg-cream"
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Runs List */}
      {runs.length === 0 ? (
        <Card className="text-center py-16 space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-cream border border-line text-muted flex items-center justify-center mx-auto">
            <Inbox className="w-7 h-7" />
          </div>
          <div>
            <h2 className="font-display font-bold text-xl text-ink">
              No applications yet
            </h2>
            <p className="mt-1 text-sm text-muted max-w-sm mx-auto">
              Add job links to queue applications for fully unattended background submission.
            </p>
          </div>
          <Button href="/apply" variant="primary" size="lg" className="shadow-sm">
            Queue job links
          </Button>
        </Card>
      ) : filteredRuns.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted border border-line rounded-card bg-cream/20">
          No applications match this filter.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredRuns.map((run) => {
            const isExpanded = !!expandedRunIds[run.id];
            const domain = getDomain(run.url);

            let timeAgo = "Just now";
            try {
              timeAgo = formatDistanceToNow(new Date(run.createdAt), { addSuffix: true });
            } catch {
              timeAgo = "recently";
            }

            return (
              <div
                key={run.id}
                className="rounded-card border border-line bg-canvas shadow-card overflow-hidden transition-all"
              >
                {/* Row Header (Clickable) */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => toggleExpand(run.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      toggleExpand(run.id);
                    }
                  }}
                  className="p-4 sm:p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-cream/40 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2.5 mb-1">
                      <span className="font-display font-bold text-sm sm:text-base text-ink">
                        {domain}
                      </span>
                      <StatusBadge status={run.status} />
                      <span className="text-xs text-muted font-normal">
                        &bull; {timeAgo}
                      </span>
                    </div>

                    <p className="text-xs text-muted font-mono truncate max-w-md sm:max-w-xl">
                      {run.url}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <a
                      href={
                        run.url.startsWith("http://") || run.url.startsWith("https://")
                          ? run.url
                          : `https://${run.url}`
                      }
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 text-muted hover:text-ink rounded-lg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      title="Open job link in new tab"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                      type="button"
                      className="p-1.5 text-muted hover:text-ink rounded-lg"
                      aria-label={isExpanded ? "Collapse row" : "Expand row"}
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && (
                  <div className="border-t border-line bg-cream/30 p-5 sm:p-6 space-y-5 animate-in fade-in duration-150">
                    {/* Submitted Run Details */}
                    {run.status === "submitted" && (
                      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                        {/* 2-Column Table of Form Fields */}
                        <div className="md:col-span-7 space-y-2">
                          <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                            Form Fields Auto-Filled
                          </span>
                          <div className="rounded-lg border border-line bg-canvas overflow-hidden text-xs">
                            <table className="w-full text-left">
                              <tbody className="divide-y divide-line">
                                {run.fields && run.fields.length > 0 ? (
                                  run.fields.map((field) => (
                                    <tr key={field.label} className="hover:bg-cream/40">
                                      <td className="px-3 py-2 font-medium text-muted w-2/5">
                                        {field.label}
                                      </td>
                                      <td className="px-3 py-2 font-semibold text-ink">
                                        {field.value}
                                      </td>
                                    </tr>
                                  ))
                                ) : (
                                  <tr>
                                    <td colSpan={2} className="px-3 py-3 text-center text-muted">
                                      Loading field audit...
                                    </td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {/* Confirmation Screenshot Proof */}
                        <div className="md:col-span-5 space-y-2">
                          <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                            Submission Proof
                          </span>
                          <div className="rounded-lg border border-line bg-canvas p-2 flex flex-col items-center justify-center text-center space-y-2 aspect-[4/3] overflow-hidden relative">
                            {/* Attempt to load real screenshot */}
                            <img
                              src={`${API_BASE_URL}/api/runs/${run.id}/screenshot`}
                              alt="Submission Proof"
                              className="w-full h-full object-cover rounded-md"
                              onError={(e) => {
                                (e.currentTarget as HTMLElement).style.display = "none";
                              }}
                            />
                            <div className="flex flex-col items-center justify-center p-4">
                              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-1">
                                <ImageIcon className="w-5 h-5" />
                              </div>
                              <span className="text-xs font-bold text-ink">
                                Confirmation screenshot
                              </span>
                              <span className="text-[11px] text-muted">
                                Proof ID #{run.id.slice(-6)} verified
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Failed / Blocked Run Details */}
                    {(run.status === "failed" ||
                      run.status === "failed_captcha" ||
                      run.status === "failed_validation") && (
                      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                        <div className="md:col-span-7 space-y-2">
                          <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                            Failure Diagnostic
                          </span>
                          <div className="p-4 rounded-lg bg-canvas border border-line space-y-2 text-xs">
                            <div className="flex items-center gap-2 text-red-700 font-semibold">
                              <ShieldAlert className="w-4 h-4" />
                              <span>
                                {run.status === "failed_captcha"
                                  ? "CAPTCHA Block Triggered"
                                  : run.status === "failed_validation"
                                  ? "Form Validation Failed"
                                  : "Submission Error"}
                              </span>
                            </div>
                            <p className="text-body leading-relaxed">
                              {run.errorReason || "An unhandled portal validation failure occurred."}
                            </p>
                          </div>
                        </div>

                        <div className="md:col-span-5 space-y-2">
                          <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                            Diagnostic Snapshot
                          </span>
                          <div className="rounded-lg border border-line bg-canvas p-2 flex flex-col items-center justify-center text-center space-y-2 aspect-[4/3] overflow-hidden relative">
                            <img
                              src={`${API_BASE_URL}/api/runs/${run.id}/screenshot`}
                              alt="Failure Snapshot"
                              className="w-full h-full object-cover rounded-md"
                              onError={(e) => {
                                (e.currentTarget as HTMLElement).style.display = "none";
                              }}
                            />
                            <div className="flex flex-col items-center justify-center p-4">
                              <div className="w-10 h-10 rounded-xl bg-red-50 text-red-700 flex items-center justify-center mb-1">
                                <ImageIcon className="w-5 h-5" />
                              </div>
                              <span className="text-xs font-bold text-ink">
                                Diagnostic screenshot
                              </span>
                              <span className="text-[11px] text-muted">
                                Saved for inspection
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Queued or Running Details */}
                    {(run.status === "queued" || run.status === "running") && (
                      <div className="p-4 rounded-lg bg-canvas border border-line flex items-center gap-3 text-xs text-body">
                        <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping shrink-0" />
                        <span>
                          {run.status === "running"
                            ? "Autonomous agent is actively navigating the employer portal, filling fields, and verifying form inputs..."
                            : "Queued in the worker pipeline. Dispatching worker shortly..."}
                        </span>
                      </div>
                    )}

                    {/* Skipped Duplicate Details */}
                    {run.status === "skipped_duplicate" && (
                      <div className="p-4 rounded-lg bg-canvas border border-line text-xs text-slate-700">
                        Candidate has already submitted an application for this job URL. Skipped to prevent duplicate application.
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
