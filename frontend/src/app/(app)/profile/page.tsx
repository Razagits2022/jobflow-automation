"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAppStore, CandidateProfile } from "@/lib/store";
import { Card, Button, Field } from "@/components/ui";
import {
  FileText,
  ArrowUpRight,
  CheckCircle2,
  Upload,
  Sparkles,
} from "lucide-react";

interface ProfileFormValues {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  resumeSummary: string;
}

const profileSchema = z.object({
  fullName: z.string().min(2, "Full name is required"),
  email: z.string().email("Please enter a valid email"),
  phone: z.string().min(7, "Please enter a valid phone number"),
  location: z.string().min(2, "Location is required"),
  resumeSummary: z.string().max(8000, "Resume summary must be 8,000 characters or less"),
});

export default function ProfilePage() {
  const router = useRouter();
  const profile = useAppStore((state) => state.profile);
  const resumeFileName = useAppStore((state) => state.resumeFileName);
  const updateProfile = useAppStore((state) => state.updateProfile);
  const loadProfile = useAppStore((state) => state.loadProfile);

  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    values: profile
      ? {
          fullName: profile.fullName || "",
          email: profile.email || "",
          phone: profile.phone || "",
          location: profile.location || "",
          resumeSummary: profile.resumeSummary || "",
        }
      : undefined,
  });

  const resumeSummaryValue = watch("resumeSummary") || "";
  const charCount = resumeSummaryValue.length;

  const onSubmit = async (data: ProfileFormValues) => {
    const updated: CandidateProfile = {
      ...(profile || {}),
      ...data,
    };
    await updateProfile(updated);
    setSaveSuccess(true);
    router.push("/apply");
  };

  // Empty state if no profile exists yet
  if (!profile) {
    return (
      <div className="max-w-xl mx-auto text-center py-12 space-y-6">
        <Card className="space-y-6 py-12">
          <div className="w-14 h-14 rounded-2xl bg-accent-soft text-accent flex items-center justify-center mx-auto">
            <Upload className="w-7 h-7" />
          </div>
          <div>
            <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-ink">
              Upload your resume to build your profile
            </h1>
            <p className="mt-2 text-sm text-muted max-w-md mx-auto">
              We extract your contact information, experience, and skills automatically to populate your applications.
            </p>
          </div>
          <Button href="/onboarding" variant="primary" size="lg" className="shadow-sm">
            Upload resume
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-ink tracking-tight">
            Your profile
          </h1>
          <p className="mt-1 text-sm sm:text-base text-body">
            This is what we use to fill your applications.
          </p>
        </div>

        {/* Resume on file chip */}
        <div className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-card bg-cream border border-line text-xs">
          <FileText className="w-4 h-4 text-accent" />
          <span className="font-semibold text-ink truncate max-w-[140px] sm:max-w-[180px]">
            {resumeFileName || "Resume on file"}
          </span>
          <Link
            href="/onboarding"
            className="text-accent hover:underline font-semibold flex items-center gap-0.5 ml-1"
          >
            <span>Replace</span>
            <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Profile Form Card */}
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* 1. Full name & 2. Email address */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Full name" error={errors.fullName?.message} required>
              <input
                type="text"
                {...register("fullName")}
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
              />
            </Field>

            <Field label="Email address" error={errors.email?.message} required>
              <input
                type="email"
                {...register("email")}
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
              />
            </Field>
          </div>

          {/* 3. Phone number & 4. Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Phone number" error={errors.phone?.message} required>
              <input
                type="tel"
                {...register("phone")}
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono text-sm"
              />
            </Field>

            <Field label="Location" error={errors.location?.message} required>
              <input
                type="text"
                {...register("location")}
                placeholder="e.g. Austin, TX (or Remote)"
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
              />
            </Field>
          </div>

          {/* 5. Resume summary */}
          <div className="space-y-2 pt-2 border-t border-line">
            <Field
              label="Resume summary"
              hint="AI uses this detailed summary to tailor applications, answer custom questions, and write cover letters."
              error={errors.resumeSummary?.message}
              required
            >
              <div className="relative">
                <textarea
                  rows={14}
                  {...register("resumeSummary")}
                  placeholder="Paste or edit your career summary, job titles, years of experience, core skills, key accomplishments, and education..."
                  className="w-full px-3.5 py-3 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all font-mono leading-relaxed resize-y min-h-[280px]"
                />
                <div className="flex justify-between items-center text-xs mt-1.5 px-0.5">
                  <span className="text-muted flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-accent" />
                    <span>Extracted automatically with AI — edit freely anytime</span>
                  </span>
                  <span
                    className={`font-mono text-xs font-semibold ${
                      charCount > 5000
                        ? "text-red-600"
                        : charCount >= 4500
                        ? "text-amber-600"
                        : "text-muted"
                    }`}
                  >
                    {charCount.toLocaleString()} / 5,000
                  </span>
                </div>
              </div>
            </Field>
          </div>

          {/* 7. Resume on file chip & 8. Save button */}
          <div className="pt-6 border-t border-line flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
            <div className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-card bg-cream border border-line text-xs">
              <FileText className="w-4 h-4 text-accent shrink-0" />
              <span className="font-semibold text-ink truncate max-w-[180px] sm:max-w-[220px]">
                {resumeFileName || "Resume on file"}
              </span>
              <Link
                href="/onboarding"
                className="text-accent hover:underline font-semibold flex items-center gap-0.5 ml-auto sm:ml-1 shrink-0"
              >
                <span>Replace</span>
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="flex items-center gap-3 justify-end">
              {saveSuccess && (
                <div className="flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3.5 py-2 rounded-pill animate-in fade-in duration-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Saved</span>
                </div>
              )}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={isSubmitting}
                className="font-bold shadow-sm"
              >
                Save &amp; continue to Apply &rarr;
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
}
