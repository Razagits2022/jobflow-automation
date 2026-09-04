"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAppStore, CandidateProfile } from "@/lib/store";
import { Card, Button, Field } from "@/components/ui";
import { FileText, ArrowUpRight, CheckCircle2, Plus, X, Upload } from "lucide-react";

interface ProfileFormValues {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  title: string;
  yearsExperience: number;
  workAuthorized: boolean;
  education: string;
}

const profileSchema = z.object({
  fullName: z.string().min(2, "Full name is required"),
  email: z.string().email("Please enter a valid email"),
  phone: z.string().min(7, "Please enter a valid phone number"),
  location: z.string().min(2, "Location is required"),
  title: z.string().min(2, "Current title is required"),
  yearsExperience: z.number().min(0, "Years must be 0 or more"),
  workAuthorized: z.boolean(),
  education: z.string().min(2, "Education is required"),
});

export default function ProfilePage() {
  const router = useRouter();
  const profile = useAppStore((state) => state.profile);
  const resumeFileName = useAppStore((state) => state.resumeFileName);
  const updateProfile = useAppStore((state) => state.updateProfile);
  const loadProfile = useAppStore((state) => state.loadProfile);

  const [skills, setSkills] = useState<string[]>(() => profile?.skills || []);
  const [prevProfile, setPrevProfile] = useState(profile);
  const [skillInput, setSkillInput] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);


  // Sync skills if profile reference changes without calling setState in an effect
  if (profile !== prevProfile) {
    setPrevProfile(profile);
    setSkills(profile?.skills || []);
  }

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    values: profile
      ? {
          fullName: profile.fullName,
          email: profile.email,
          phone: profile.phone,
          location: profile.location,
          title: profile.title,
          yearsExperience: profile.yearsExperience,
          workAuthorized: profile.workAuthorized,
          education: profile.education,
        }
      : undefined,
  });

  const handleAddSkill = () => {
    const trimmed = skillInput.trim().replace(/,/g, "");
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setSkillInput("");
    }
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      handleAddSkill();
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkills(skills.filter((s) => s !== skillToRemove));
  };

  const onSubmit = async (data: ProfileFormValues) => {
    const updated: CandidateProfile = {
      ...data,
      skills,
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

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div className="sm:col-span-2">
              <Field label="Current job title" error={errors.title?.message} required>
                <input
                  type="text"
                  {...register("title")}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
                />
              </Field>
            </div>

            <div>
              <Field
                label="Years of experience"
                error={errors.yearsExperience?.message}
                required
              >
                <input
                  type="number"
                  min="0"
                  step="1"
                  {...register("yearsExperience")}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
                />
              </Field>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Highest education" error={errors.education?.message} required>
              <input
                type="text"
                {...register("education")}
                placeholder="e.g. BS Computer Science"
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
              />
            </Field>

            <Field label="US work authorization" required>
              <select
                {...register("workAuthorized", {
                  setValueAs: (v) => v === "true" || v === true,
                })}
                className="w-full px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all cursor-pointer"
              >
                <option value="true">Yes — Authorized to work in the US</option>
                <option value="false">No — Requires visa sponsorship</option>
              </select>
            </Field>
          </div>

          {/* Skills Tag Input */}
          <div className="space-y-2 pt-2 border-t border-line">
            <Field
              label="Key skills & technologies"
              hint="Press Enter or comma to add"
            >
              <div className="flex gap-2">
                <input
                  type="text"
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={handleSkillKeyDown}
                  placeholder="e.g. React, Next.js, TypeScript"
                  className="flex-1 px-3.5 py-2.5 rounded-lg border border-line bg-canvas text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="px-4 py-2 rounded-lg bg-cream hover:bg-accent-soft text-ink font-semibold text-xs border border-line flex items-center gap-1 cursor-pointer transition-colors"
                >
                  <Plus className="w-4 h-4 text-accent" />
                  <span>Add</span>
                </button>
              </div>
            </Field>

            {/* Skills Chips */}
            <div className="flex flex-wrap gap-2 pt-2 min-h-[40px]">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-cream text-ink text-xs font-medium border border-line shadow-3xs animate-in fade-in"
                >
                  <span>{skill}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="text-muted hover:text-red-600 rounded-full cursor-pointer transition-colors"
                    aria-label={`Remove skill ${skill}`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Form Actions */}
          <div className="pt-6 border-t border-line flex items-center justify-between">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isSubmitting}
              className="font-bold shadow-sm"
            >
              Save &amp; continue to Apply &rarr;
            </Button>

            {saveSuccess && (
              <div className="flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3.5 py-2 rounded-pill animate-in fade-in duration-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Saved successfully</span>
              </div>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
