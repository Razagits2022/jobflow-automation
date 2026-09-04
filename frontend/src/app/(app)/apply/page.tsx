"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { Card, Button, Field } from "@/components/ui";
import { Plus, Upload, Trash2, Globe, Sparkles, AlertCircle } from "lucide-react";

const EXAMPLE_PLACEHOLDER = `https://careers.pipercompanies.com/details/173312/frontend_software_engineer
https://www.pensioncareers.co.uk/jobs/11494657/pension-calculation-analyst.asp
https://www.jobsandcareersmag.com/jobpost/business-development-manager-61/`;

function getDomain(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return "external job";
  }
}

export default function ApplyPage() {
  const router = useRouter();
  const jobs = useAppStore((state) => state.jobs);
  const loadJobs = useAppStore((state) => state.loadJobs);
  const addJobs = useAppStore((state) => state.addJobs);
  const removeJob = useAppStore((state) => state.removeJob);
  const startApplying = useAppStore((state) => state.startApplying);

  const [textareaValue, setTextareaValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleAddTextareaUrls = async () => {
    const lines = textareaValue
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length > 0) {
      await addJobs(lines);
      setTextareaValue("");
    }
  };

  const handleCsvUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target?.result as string;
      if (!text) return;

      // Split on newlines, commas, quotes, semicolons
      const tokens = text.split(/[\r\n,;"']+/);
      const urlRegex = /(https?:\/\/[^\s]+)/gi;
      const extractedUrls: string[] = [];

      for (const token of tokens) {
        const trimmed = token.trim();
        const matches = trimmed.match(urlRegex);
        if (matches) {
          extractedUrls.push(...matches);
        } else if (trimmed.includes("http://") || trimmed.includes("https://")) {
          extractedUrls.push(trimmed);
        }
      }

      if (extractedUrls.length > 0) {
        await addJobs(extractedUrls);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleStartApplying = async () => {
    if (jobs.length === 0 || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await startApplying();
      router.push("/runs");
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="border-b border-line pb-6">
        <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
          Apply to jobs
        </h1>
        <p className="mt-1 text-sm sm:text-base text-body">
          Paste job posting links. We open each one, fill the application, and submit it for you.
        </p>
        <p className="text-xs text-muted mt-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Soon these links will arrive automatically from your job search.</span>
        </p>
      </div>

      {/* Input Form Card */}
      <Card className="space-y-5">
        <Field
          label="Job URLs, one per line"
          hint="Greenhouse, Workday, Lever, iCIMS, or any custom career portal"
        >
          <textarea
            rows={5}
            value={textareaValue}
            onChange={(e) => setTextareaValue(e.target.value)}
            placeholder={EXAMPLE_PLACEHOLDER}
            className="w-full p-3.5 rounded-lg border border-line bg-canvas text-xs sm:text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono leading-relaxed placeholder:text-muted/60"
          />
        </Field>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleAddTextareaUrls}
              disabled={!textareaValue.trim()}
              className="font-semibold"
            >
              <Plus className="w-4 h-4 text-accent" />
              <span>Add URLs</span>
            </Button>

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 rounded-pill bg-canvas hover:bg-cream text-body hover:text-ink text-xs font-semibold border border-line flex items-center gap-1.5 transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <Upload className="w-3.5 h-3.5 text-muted" />
              <span>Upload CSV</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              className="hidden"
            />
          </div>

          <button
            type="button"
            onClick={() => setTextareaValue(EXAMPLE_PLACEHOLDER)}
            className="text-xs text-muted hover:text-accent font-medium underline underline-offset-2 cursor-pointer transition-colors"
          >
            Insert sample URLs
          </button>
        </div>
      </Card>

      {/* Queued Jobs List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-lg text-ink">
            Queued Applications ({jobs.length})
          </h2>
          {jobs.length > 0 && (
            <span className="text-xs text-muted font-normal">
              Ready for autonomous dispatch
            </span>
          )}
        </div>

        {jobs.length === 0 ? (
          <div className="p-8 rounded-card border border-line bg-cream/20 text-center space-y-2">
            <AlertCircle className="w-6 h-6 text-muted mx-auto" />
            <p className="text-sm font-medium text-ink">No job URLs in queue</p>
            <p className="text-xs text-muted max-w-sm mx-auto">
              Paste URLs above or upload a CSV to queue job applications for automated background submission.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-line rounded-card border border-line bg-canvas overflow-hidden shadow-card">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-cream/30 transition-colors"
              >
                <div className="min-w-0 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-cream border border-line flex items-center justify-center shrink-0 mt-0.5">
                    <Globe className="w-4 h-4 text-muted" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs sm:text-sm text-ink truncate">
                        {getDomain(job.url)}
                      </span>
                      <span className="text-[10px] font-semibold text-accent bg-accent-soft px-2 py-0.5 rounded-pill uppercase">
                        Pending
                      </span>
                    </div>
                    <p className="text-xs text-muted font-mono truncate mt-0.5">
                      {job.url}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => removeJob(job.id)}
                  className="p-2 text-muted hover:text-red-600 rounded-lg transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Remove URL"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Start Applying Dispatch Action */}
        <div className="pt-2">
          <Button
            type="button"
            variant="primary"
            size="lg"
            disabled={jobs.length === 0}
            onClick={handleStartApplying}
            className="w-full sm:w-auto font-bold shadow-sm"
          >
            Start applying ({jobs.length})
          </Button>
        </div>
      </div>
    </div>
  );
}
