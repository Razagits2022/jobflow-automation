import React from "react";
import clsx from "clsx";

interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  size?: "default" | "sm" | "wide";
}

export function Container({
  children,
  className,
  size = "default",
  ...props
}: ContainerProps) {
  const sizeClasses = {
    sm: "max-w-2xl",
    default: "max-w-[1120px]",
    wide: "max-w-[1240px]",
  };

  return (
    <div
      className={clsx(
        "w-full mx-auto px-4 sm:px-6 md:px-8",
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
