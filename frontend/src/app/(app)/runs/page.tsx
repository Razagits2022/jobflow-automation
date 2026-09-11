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
  Maximize2,
  ZoomIn,
  X,
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

function formatFieldLabel(raw: string): string {
  if (!raw) return "Field";
  if (raw.startsWith("[data-jf-id")) return "Consent / Site Cookies";
  const s = raw
    .replace(/^#/, "")
    .replace(/^input\[name="/i, "")
    .replace(/"\]$/i, "")
    .replace(/\[/g, " ")
    .replace(/\]/g, " ")
    .replace(/application_form_application_/gi, "")
    .replace(/application_form_/gi, "")
    .replace(/equality_monitoring_/gi, "")
    .replace(/_text_answer/gi, "")
    .replace(/_boolean_answer/gi, "")
    .replace(/_attributes_\d+/gi, "")
    .replace(/_attributes_/gi, " ")
    .replace(/_/g, " ")
    .replace(/\\/g, "")
    .trim();

  if (s.length > 3 && s[0] === s[0].toUpperCase() && !s.includes("_")) {
    return s;
  }

  return s
    .split(/\s+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

function formatFieldValue(val: string) {
  if (val === "true") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
        Yes
      </span>
    );
  }
  if (val === "false") {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-cream text-muted border border-line">
        No
      </span>
    );
  }
  if (!val || val.toLowerCase() === "none" || val === "null") {
    return <span className="text-muted italic">—</span>;
  }
  return <span className="break-words font-medium text-ink">{val}</span>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RunsPage() {
  const runs = useAppStore((state) => state.runs);
  const loadRuns = useAppStore((state) => state.loadRuns);
  const loadRunDetails = useAppStore((state) => state.loadRunDetails);

  const [filterTab, setFilterTab] = useState<FilterTab>("all");
  const [expandedRunIds, setExpandedRunIds] = useState<Record<string, boolean>>({});
  const [previewModal, setPreviewModal] = useState<{ url: string; title: string } | null>(null);

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
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                              Form Fields Auto-Filled
                            </span>
                            <span className="text-[11px] font-semibold text-muted bg-canvas border border-line px-2 py-0.5 rounded">
                              {run.fields ? `${run.fields.length} fields` : "0 fields"}
                            </span>
                          </div>
                          <div className="rounded-lg border border-line bg-canvas overflow-hidden text-xs max-h-80 overflow-y-auto">
                            <table className="w-full text-left">
                              <tbody className="divide-y divide-line">
                                {run.fields && run.fields.length > 0 ? (
                                  run.fields.map((field) => (
                                    <tr key={field.label} className="hover:bg-cream/40 transition-colors">
                                      <td className="px-3 py-2 font-medium text-body w-1/2">
                                        {formatFieldLabel(field.label)}
                                      </td>
                                      <td className="px-3 py-2 text-ink">
                                        {formatFieldValue(field.value)}
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
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                              Submission Proof
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                setPreviewModal({
                                  url: `${API_BASE_URL}/api/runs/${run.id}/screenshot`,
                                  title: `Submission Proof — ${getDomain(run.url)}`,
                                })
                              }
                              className="text-[11px] font-semibold text-brand hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <Maximize2 className="w-3 h-3" />
                              View Full Size
                            </button>
                          </div>
                          <div
                            onClick={() =>
                              setPreviewModal({
                                url: `${API_BASE_URL}/api/runs/${run.id}/screenshot`,
                                title: `Submission Proof — ${getDomain(run.url)}`,
                              })
                            }
                            className="rounded-lg border border-line bg-canvas overflow-hidden relative group cursor-pointer hover:border-brand/60 shadow-sm transition-all"
                          >
                            <div className="relative w-full h-56 bg-stone-100 flex items-center justify-center overflow-hidden">
                              <img
                                src={`${API_BASE_URL}/api/runs/${run.id}/screenshot`}
                                alt="Submission Proof"
                                className="w-full h-full object-contain object-top transition-transform duration-200 group-hover:scale-[1.01]"
                                onError={(e) => {
                                  (e.currentTarget as HTMLElement).style.display = "none";
                                }}
                              />
                              <div className="absolute inset-0 bg-ink/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-white font-semibold text-xs backdrop-blur-[1px]">
                                <ZoomIn className="w-4 h-4" />
                                <span>Click to inspect snapshot</span>
                              </div>
                            </div>
                            <div className="p-3 bg-canvas border-t border-line flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2 text-emerald-700 font-semibold">
                                <div className="w-6 h-6 rounded-lg bg-emerald-50 flex items-center justify-center">
                                  <ImageIcon className="w-3.5 h-3.5" />
                                </div>
                                <span>Confirmed Proof</span>
                              </div>
                              <span className="text-[11px] text-muted">
                                #{run.id.slice(-6)}
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
                            <p className="text-body leading-relaxed break-words">
                              {run.errorReason || "An unhandled portal validation failure occurred."}
                            </p>
                          </div>
                        </div>

                        <div className="md:col-span-5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-ink uppercase tracking-wider block">
                              Diagnostic Snapshot
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                setPreviewModal({
                                  url: `${API_BASE_URL}/api/runs/${run.id}/screenshot`,
                                  title: `Diagnostic Snapshot — ${getDomain(run.url)}`,
                                })
                              }
                              className="text-[11px] font-semibold text-brand hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <Maximize2 className="w-3 h-3" />
                              View Full Size
                            </button>
                          </div>
                          <div
                            onClick={() =>
                              setPreviewModal({
                                url: `${API_BASE_URL}/api/runs/${run.id}/screenshot`,
                                title: `Diagnostic Snapshot — ${getDomain(run.url)}`,
                              })
                            }
                            className="rounded-lg border border-line bg-canvas overflow-hidden relative group cursor-pointer hover:border-red-400 shadow-sm transition-all"
                          >
                            <div className="relative w-full h-56 bg-stone-100 flex items-center justify-center overflow-hidden">
                              <img
                                src={`${API_BASE_URL}/api/runs/${run.id}/screenshot`}
                                alt="Failure Snapshot"
                                className="w-full h-full object-contain object-top transition-transform duration-200 group-hover:scale-[1.01]"
                                onError={(e) => {
                                  (e.currentTarget as HTMLElement).style.display = "none";
                                }}
                              />
                              <div className="absolute inset-0 bg-ink/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-white font-semibold text-xs backdrop-blur-[1px]">
                                <ZoomIn className="w-4 h-4" />
                                <span>Click to inspect error page</span>
                              </div>
                            </div>
                            <div className="p-3 bg-canvas border-t border-line flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2 text-red-700 font-semibold">
                                <div className="w-6 h-6 rounded-lg bg-red-50 flex items-center justify-center">
                                  <ImageIcon className="w-3.5 h-3.5" />
                                </div>
                                <span>Error Captured</span>
                              </div>
                              <span className="text-[11px] text-muted">
                                #{run.id.slice(-6)}
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

      {/* Full-Resolution Screenshot Lightbox Modal */}
      {previewModal && (
        <div
          className="fixed inset-0 z-50 bg-ink/80 backdrop-blur-sm flex flex-col items-center justify-center p-3 sm:p-6 animate-in fade-in duration-150"
          onClick={() => setPreviewModal(null)}
        >
          <div
            className="bg-canvas border border-line rounded-xl shadow-2xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-line bg-cream/40">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-brand" />
                <span className="text-sm font-bold text-ink truncate max-w-lg">
                  {previewModal.title}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={previewModal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-ink bg-white border border-line hover:bg-cream transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open Raw Image
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewModal(null)}
                  className="p-1.5 rounded-lg text-muted hover:text-ink hover:bg-line/50 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal Scrollable Image Body */}
            <div className="flex-1 overflow-auto p-4 bg-stone-100 flex items-start justify-center">
              <img
                src={previewModal.url}
                alt="Full application screenshot proof"
                className="max-w-full h-auto rounded shadow-sm border border-line"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
