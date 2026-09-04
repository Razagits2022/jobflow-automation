import React from "react";
import Link from "next/link";
import clsx from "clsx";

export type ButtonVariant = "primary" | "outline" | "ghost" | "secondary";
export type ButtonSize = "sm" | "md" | "lg";

interface BaseButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: React.ReactNode;
}

export type ButtonProps = BaseButtonProps &
  (
    | (React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined })
    | (React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string })
  );

export const Button = React.forwardRef<
  HTMLButtonElement | HTMLAnchorElement,
  ButtonProps
>(function Button(
  { variant = "primary", size = "md", className, children, href, ...props },
  ref
) {
  const baseClasses =
    "inline-flex items-center justify-center font-medium transition-all duration-150 outline-none select-none disabled:opacity-50 disabled:pointer-events-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 cursor-pointer";

  const sizeClasses = {
    sm: "text-xs px-4 py-2 gap-1.5 rounded-pill",
    md: "text-sm px-6 py-2.5 gap-2 rounded-pill font-medium",
    lg: "text-base px-7 py-3.5 gap-2.5 rounded-pill font-semibold",
  };

  const variantClasses = {
    primary:
      "bg-accent text-white hover:bg-accent-hover active:scale-[0.98] shadow-xs",
    outline:
      "bg-transparent border border-line text-ink hover:bg-cream active:scale-[0.98]",
    ghost:
      "bg-transparent text-body hover:text-ink active:text-ink hover:bg-cream rounded-pill px-3 py-2",
    secondary:
      "bg-cream text-ink hover:bg-accent-soft active:scale-[0.98]",
  };

  const combinedClasses = clsx(
    baseClasses,
    sizeClasses[size],
    variantClasses[variant],
    className
  );

  if (href) {
    return (
      <Link
        href={href}
        ref={ref as React.Ref<HTMLAnchorElement>}
        className={combinedClasses}
        {...(props as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
      >
        {children}
      </Link>
    );
  }

  return (
    <button
      ref={ref as React.Ref<HTMLButtonElement>}
      className={combinedClasses}
      {...(props as React.ButtonHTMLAttributes<HTMLButtonElement>)}
    >
      {children}
    </button>
  );
});
