import React from "react";
import clsx from "clsx";

interface StatProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function Stat({ label, value, subtext, icon, className }: StatProps) {
  return (
    <div
      className={clsx(
        "bg-canvas border border-line rounded-card shadow-card p-6 flex flex-col justify-between text-left transition-all",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <span className="text-xs sm:text-sm font-medium text-muted">
          {label}
        </span>
        {icon && <div className="text-accent">{icon}</div>}
      </div>

      <div className="flex flex-col">
        <span className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
          {value}
        </span>
        {subtext && (
          <span className="mt-1 text-xs text-muted font-normal">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
}
