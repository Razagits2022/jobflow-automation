import React from "react";
import clsx from "clsx";

interface FieldProps {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}

export function Field({
  label,
  error,
  hint,
  required,
  className,
  children,
}: FieldProps) {
  return (
    <div className={clsx("flex flex-col gap-1.5 text-left", className)}>
      <label className="text-xs sm:text-sm font-semibold text-ink flex items-center justify-between">
        <span>
          {label}
          {required && <span className="text-accent ml-0.5">*</span>}
        </span>
        {hint && <span className="text-[11px] font-normal text-muted">{hint}</span>}
      </label>

      {children}

      {error && (
        <span className="text-xs font-medium text-red-600 mt-0.5">
          {error}
        </span>
      )}
    </div>
  );
}
