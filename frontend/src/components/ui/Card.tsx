import React from "react";
import clsx from "clsx";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={clsx(
        "bg-canvas border border-line rounded-card shadow-card p-6 sm:p-8",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
