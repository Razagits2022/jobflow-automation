import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";
import clsx from "clsx";

interface LogoProps {
  href?: string;
  className?: string;
  variant?: "dark" | "light";
}

export function Logo({ href = "/", className, variant = "dark" }: LogoProps) {
  const content = (
    <div className={clsx("inline-flex items-center gap-2.5 select-none", className)}>
      {/* Geometric mark: JobFlow flow arrow / layered accent shapes */}
      <div className="relative w-7 h-7 flex items-center justify-center" aria-hidden="true">
        <span
          className={clsx(
            "w-5 h-5 rounded-[6px] rotate-[-6deg]",
            variant === "dark" ? "bg-ink" : "bg-white/20"
          )}
        />
        <span className="absolute w-4 h-4 rounded-[5px] bg-accent rotate-[12deg] opacity-95 shadow-2xs" />
      </div>
      <span
        className={clsx(
          "font-display font-extrabold text-xl tracking-tight",
          variant === "dark" ? "text-ink" : "text-white"
        )}
      >
        {BRAND_NAME}
      </span>
    </div>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-lg transition-transform active:scale-95"
      >
        {content}
      </Link>
    );
  }

  return content;
}
