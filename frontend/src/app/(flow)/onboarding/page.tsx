"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { Card, Button, Dropzone } from "@/components/ui";
import { FileText, X, Loader2, Sparkles, AlertCircle } from "lucide-react";

export function OnboardingPage() {
  const router = useRouter();
  const subscribed = useAppStore((state) => state.subscribed);
  const analyzeResume = useAppStore((state) => state.analyzeResume);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Guard: if not subscribed, redirect to /subscribe
  useEffect(() => {
    if (!subscribed) {
      router.replace("/subscribe");
    }
  }, [subscribed, router]);

  const handleFile = (file: File) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      await analyzeResume(selectedFile);
      router.push("/profile");
    } catch (err: unknown) {
      setIsAnalyzing(false);
      let message = "Failed to analyze resume. Please try a different PDF or Word document.";
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        if (axiosErr.response?.data?.detail) {
          message = axiosErr.response.data.detail;
        }
      }
      setErrorMessage(message);
    }
  };

  if (!subscribed) {
    return null;
  }

  return (
    <div className="w-full max-w-lg mx-auto text-center space-y-8">
      {/* Heading */}
      <div>
        <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
          Upload your resume
        </h1>
        <p className="mt-2 text-sm sm:text-base text-body max-w-md mx-auto">
          We read it once and fill your profile automatically. You can edit anything after.
        </p>
      </div>

      {/* Main Upload Card */}
      <Card className="text-left space-y-6">
        {isAnalyzing ? (
          /* Analyzing In-Place Loading State */
          <div className="py-14 sm:py-18 text-center flex flex-col items-center justify-center space-y-4 animate-in fade-in duration-200">
            <div className="w-14 h-14 rounded-2xl bg-accent-soft text-accent flex items-center justify-center shadow-sm">
              <Loader2 className="w-7 h-7 animate-spin" />
            </div>
            <div className="space-y-1">
              <h2 className="font-display font-bold text-xl text-ink">
                Reading your resume...
              </h2>
              <p className="text-sm text-muted">
                Extracting contact details, work history, and core skills
              </p>
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-cream text-xs text-body border border-line mt-2">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              <span>Simulating AI perception</span>
            </div>
          </div>
        ) : (
          <>
            {/* File Dropzone */}
            {!selectedFile ? (
              <Dropzone onFile={handleFile} />
            ) : (
              /* Selected File Preview Box */
              <div className="p-5 rounded-card border border-line bg-cream/30 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-accent-soft text-accent flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 stroke-[2]" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-sm text-ink truncate">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-muted">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready for analysis
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="p-1.5 rounded-lg text-muted hover:text-ink hover:bg-black/5 transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Remove file"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Error message alert */}
            {errorMessage && (
              <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2 animate-in fade-in">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-600" />
                <span className="leading-relaxed">{errorMessage}</span>
              </div>
            )}

            {/* Action Button */}
            <Button
              type="button"
              variant="primary"
              size="lg"
              disabled={!selectedFile}
              onClick={handleAnalyze}
              className="w-full font-bold shadow-sm"
            >
              Analyze resume
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}

export default OnboardingPage;
