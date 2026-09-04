import React from "react";
import { RunStatus } from "@/lib/store";
import { CheckCircle2, Clock, AlertTriangle, XCircle, FileWarning, CheckCheck } from "lucide-react";
import clsx from "clsx";

interface StatusBadgeProps {
  status: RunStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  switch (status) {
    case "submitted":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <CheckCircle2 className="w-3.5 h-3.5 stroke-[2.5]" />
          <span>Submitted</span>
        </span>
      );
    case "running":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse motion-reduce:animate-none" />
          <span>Applying...</span>
        </span>
      );
    case "queued":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-cream text-body border border-line text-xs font-medium tracking-wide",
            className
          )}
        >
          <Clock className="w-3.5 h-3.5 text-muted" />
          <span>Queued</span>
        </span>
      );
    case "failed_captcha":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <AlertTriangle className="w-3.5 h-3.5 stroke-[2.2]" />
          <span>Blocked (CAPTCHA)</span>
        </span>
      );
    case "failed_validation":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-purple-50 text-purple-700 border border-purple-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <FileWarning className="w-3.5 h-3.5 stroke-[2.2]" />
          <span>Form Error</span>
        </span>
      );
    case "skipped_duplicate":
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <CheckCheck className="w-3.5 h-3.5 stroke-[2.2]" />
          <span>Already Applied</span>
        </span>
      );
    case "failed":
    default:
      return (
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-red-50 text-red-700 border border-red-200 text-xs font-semibold tracking-wide",
            className
          )}
        >
          <XCircle className="w-3.5 h-3.5 stroke-[2.2]" />
          <span>Failed</span>
        </span>
      );
  }
}
