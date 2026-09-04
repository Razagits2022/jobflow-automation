import React from "react";
import clsx from "clsx";

interface BentoCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  prominent?: boolean;
}

export function BentoCard({
  children,
  title,
  subtitle,
  className,
  prominent = false,
  ...props
}: BentoCardProps) {
  return (
    <div
      className={clsx(
        "rounded-card bg-plum-800 text-white p-6 md:p-8 flex flex-col justify-between transition-colors duration-200 border border-plum-700/40 select-none",
        prominent && "shadow-soft",
        className
      )}
      {...props}
    >
      {title && (
        <h3
          className={clsx(
            "font-display font-bold text-white tracking-tight leading-tight",
            prominent
              ? "text-2xl sm:text-3xl md:text-4xl"
              : "text-lg sm:text-xl md:text-2xl"
          )}
        >
          {title}
        </h3>
      )}
      {subtitle && (
        <p className="text-plum-200/80 text-sm md:text-base mt-2 font-sans">
          {subtitle}
        </p>
      )}
      {children}
    </div>
  );
}
