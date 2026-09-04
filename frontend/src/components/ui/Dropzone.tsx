"use client";

import React, { useState, useRef } from "react";
import { UploadCloud } from "lucide-react";
import clsx from "clsx";

interface DropzoneProps {
  onFile: (file: File) => void;
  accept?: string;
  className?: string;
  disabled?: boolean;
}

export function Dropzone({
  onFile,
  accept = ".pdf,.doc,.docx",
  className,
  disabled = false,
}: DropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (disabled) return;

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFile(files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFile(files[0]);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={clsx(
        "relative rounded-card border-2 border-dashed p-8 sm:p-12 text-center transition-all cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 flex flex-col items-center justify-center gap-3.5 select-none",
        isDragOver
          ? "border-accent bg-accent-soft/50 shadow-soft scale-[1.01]"
          : "border-line bg-canvas hover:bg-cream/40 hover:border-muted",
        disabled && "opacity-50 pointer-events-none cursor-not-allowed",
        className
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleInputChange}
        className="hidden"
        tabIndex={-1}
        disabled={disabled}
      />

      <div className="w-14 h-14 rounded-2xl bg-accent-soft text-accent flex items-center justify-center mb-1 shadow-3xs">
        <UploadCloud className="w-7 h-7 stroke-[2]" />
      </div>

      <div className="space-y-1">
        <p className="font-display font-bold text-base sm:text-lg text-ink">
          Drag your resume here, or <span className="text-accent underline underline-offset-4">click to browse</span>
        </p>
        <p className="text-xs sm:text-sm text-muted">
          PDF, DOC, or DOCX (max 10MB)
        </p>
      </div>
    </div>
  );
}
