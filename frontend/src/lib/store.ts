import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiClient, apiGet, apiPost, apiDelete } from "@/lib/api";

export type RunStatus =
  | "queued"
  | "running"
  | "submitted"
  | "failed"
  | "failed_captcha"
  | "failed_validation"
  | "skipped_duplicate";

export interface CandidateProfile {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  title: string;
  yearsExperience: number;
  workAuthorized: boolean;
  education: string;
  skills: string[];
}

export interface JobUrl {
  id: string;
  url: string;
  addedAt: string;
}

export interface RunField {
  label: string;
  value: string;
}

export interface Run {
  id: string;
  url: string;
  status: RunStatus;
  createdAt: string;
  fields?: RunField[];
  errorReason?: string;
}

export interface AppState {
  subscribed: boolean;
  resumeFileName: string | null;
  profile: CandidateProfile | null;
  jobs: JobUrl[];
  runs: Run[];
  isLoading: boolean;

  subscribe: () => Promise<void>;
  analyzeResume: (file: File) => Promise<CandidateProfile>;
  loadProfile: () => Promise<void>;
  updateProfile: (profile: CandidateProfile) => Promise<void>;
  loadJobs: () => Promise<void>;
  addJobs: (urls: string[]) => Promise<void>;
  removeJob: (id: string) => Promise<void>;
  loadRuns: () => Promise<void>;
  loadRunDetails: (id: string) => Promise<void>;
  startApplying: () => Promise<void>;
  reset: () => void;
}

// Initial state
const INITIAL_STATE = {
  subscribed: false,
  resumeFileName: null,
  profile: null,
  jobs: [],
  runs: [],
  isLoading: false,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...INITIAL_STATE,

      subscribe: async () => {
        try {
          await apiPost("/api/subscribe", {});
        } catch {
          // Non-blocking
        }
        set({ subscribed: true });
      },

      analyzeResume: async (file: File) => {
        set({ resumeFileName: file.name, isLoading: true });

        try {
          const formData = new FormData();
          formData.append("file", file);

          const response = await apiClient.post<CandidateProfile>(
            "/api/candidate/resume",
            formData,
            {
              headers: {
                "Content-Type": "multipart/form-data",
              },
            }
          );

          const profileData = response.data;
          set({ profile: profileData, isLoading: false });
          return profileData;
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      loadProfile: async () => {
        try {
          const profile = await apiGet<CandidateProfile | null>("/api/candidate");
          if (profile) {
            set({ profile });
          }
        } catch (error) {
          console.error("Failed to load candidate profile", error);
        }
      },

      updateProfile: async (profile: CandidateProfile) => {
        set({ profile });
        try {
          const response = await apiClient.put<CandidateProfile>("/api/candidate", profile);
          if (response.data) {
            set({ profile: response.data });
          }
        } catch (error) {
          console.error("Failed to update candidate profile", error);
        }
      },

      loadJobs: async () => {
        try {
          const jobs = await apiGet<JobUrl[]>("/api/jobs");
          set({ jobs });
        } catch (error) {
          console.error("Failed to load queued jobs", error);
        }
      },

      addJobs: async (rawUrls: string[]) => {
        const trimmed = rawUrls.map((u) => u.trim()).filter(Boolean);
        if (trimmed.length === 0) return;

        try {
          const created = await apiPost<JobUrl[]>("/api/jobs", { urls: trimmed });
          set((state) => {
            const existingIds = new Set(state.jobs.map((j) => j.id));
            const newOnes = created.filter((j) => !existingIds.has(j.id));
            return { jobs: [...state.jobs, ...newOnes] };
          });
        } catch (error) {
          console.error("Failed to add jobs", error);
        }
      },

      removeJob: async (id: string) => {
        set((state) => ({ jobs: state.jobs.filter((j) => j.id !== id) }));
        try {
          await apiDelete(`/api/jobs/${id}`);
        } catch (error) {
          console.error("Failed to remove job", error);
        }
      },

      loadRuns: async () => {
        try {
          const runs = await apiGet<Run[]>("/api/runs");
          set({ runs });
        } catch (error) {
          console.error("Failed to load runs", error);
        }
      },

      loadRunDetails: async (id: string) => {
        try {
          const run = await apiGet<Run>(`/api/runs/${id}`);
          set((state) => ({
            runs: state.runs.map((r) => (r.id === id ? { ...r, ...run } : r)),
          }));
        } catch (error) {
          console.error("Failed to load run details", error);
        }
      },

      startApplying: async () => {
        try {
          const createdRuns = await apiPost<Run[]>("/api/runs/start", {});
          set((state) => ({
            jobs: [],
            runs: [...createdRuns, ...state.runs],
          }));
        } catch (error) {
          console.error("Failed to start applying", error);
        }
      },

      reset: () => {
        set(INITIAL_STATE);
        if (typeof window !== "undefined") {
          window.localStorage.removeItem("jobflow-app-store");
        }
      },
    }),
    {
      name: "jobflow-app-store",
      partialize: (state) => ({
        subscribed: state.subscribed,
        resumeFileName: state.resumeFileName,
      }),
    }
  )
);
