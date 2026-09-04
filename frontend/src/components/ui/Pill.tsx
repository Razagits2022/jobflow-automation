import React from "react";
import clsx from "clsx";

interface PillProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export function Pill({ children, className, ...props }: PillProps) {
  return (
    <div
      className={clsx(
        "inline-flex items-center rounded-pill border border-line bg-canvas p-1.5 shadow-xs transition-shadow focus-within:ring-2 focus-within:ring-violet-500 focus-within:border-transparent",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
