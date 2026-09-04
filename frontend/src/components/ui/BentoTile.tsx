import React from "react";
import clsx from "clsx";
import { Laptop, User, Check } from "lucide-react";

export type TileVariant = "green" | "amber" | "violet" | "photo-laptop" | "photo-portrait";

interface BentoTileProps extends React.HTMLAttributes<HTMLDivElement> {
  variant: TileVariant;
  altText: string;
  className?: string;
  children?: React.ReactNode;
}

export function BentoTile({
  variant,
  altText,
  className,
  children,
  ...props
}: BentoTileProps) {
  // TODO: replace placeholder photo tiles with real photography when available
  const variantStyles = {
    green: "bg-tile-green text-white",
    amber: "bg-tile-amber text-plum-950",
    violet: "bg-violet-200 text-plum-950",
    "photo-laptop":
      "bg-gradient-to-br from-[#E2D9F8] via-[#D2C2F7] to-[#BBA3F5] text-plum-950/70 border border-violet-200",
    "photo-portrait":
      "bg-gradient-to-br from-[#F5E6DA] via-[#EED5FF] to-[#D5C2F8] text-plum-950/70 border border-violet-200",
  };

  return (
    <div
      role="img"
      aria-label={altText}
      className={clsx(
        "rounded-card flex items-center justify-center relative overflow-hidden transition-transform duration-200 select-none p-4",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {variant === "green" && (
        <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
          <Check className="w-6 h-6 text-white stroke-[2.5]" aria-hidden="true" />
        </div>
      )}

      {variant === "photo-laptop" && (
        <div className="flex flex-col items-center justify-center text-center gap-2">
          <div className="w-12 h-12 rounded-full bg-white/60 shadow-xs flex items-center justify-center text-violet-600">
            <Laptop className="w-6 h-6" aria-hidden="true" />
          </div>
          <span className="text-xs font-medium text-plum-950/80 px-2 py-0.5 rounded-full bg-white/40">
            Applying
          </span>
        </div>
      )}

      {variant === "photo-portrait" && (
        <div className="flex flex-col items-center justify-center text-center gap-2">
          <div className="w-12 h-12 rounded-full bg-white/60 shadow-xs flex items-center justify-center text-plum-950">
            <User className="w-6 h-6" aria-hidden="true" />
          </div>
          <span className="text-xs font-medium text-plum-950/80 px-2 py-0.5 rounded-full bg-white/40">
            Candidate
          </span>
        </div>
      )}

      {children}
    </div>
  );
}
