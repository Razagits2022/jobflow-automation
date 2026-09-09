"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { CloudLightning, CheckCircle2, RefreshCw, Server, AlertCircle } from "lucide-react";
import { checkServerHealth } from "@/lib/api";

interface ServerWarmupContextType {
  isServerReady: boolean;
  isWakingUp: boolean;
  retryWarmup: () => void;
}

const ServerWarmupContext = createContext<ServerWarmupContextType>({
  isServerReady: true,
  isWakingUp: false,
  retryWarmup: () => {},
});

export const useServerWarmup = () => useContext(ServerWarmupContext);

export function ServerWarmupProvider({ children }: { children: React.ReactNode }) {
  const [isServerReady, setIsServerReady] = useState(false);
  const [isWakingUp, setIsWakingUp] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [progress, setProgress] = useState(10);
  const [statusText, setStatusText] = useState("Checking cloud server status...");
  const [isError, setIsError] = useState(false);
  const [showNotification, setShowNotification] = useState(false);

  const startWarmup = async () => {
    setIsError(false);
    setElapsedSeconds(0);
    setProgress(15);

    // Initial rapid probe (wait max 2.5s)
    const quickAwake = await checkServerHealth(2500);
    if (quickAwake) {
      setIsServerReady(true);
      setIsWakingUp(false);
      setShowNotification(false);
      return;
    }

    // Server is asleep or cold starting — reveal notification
    setIsWakingUp(true);
    setShowNotification(true);
    setStatusText("Waking up cloud server...");
  };

  useEffect(() => {
    startWarmup();
  }, []);

  // Timer & progress simulation while waking up
  useEffect(() => {
    if (!isWakingUp || isServerReady) return;

    const timer = setInterval(() => {
      setElapsedSeconds((prev) => {
        const next = prev + 1;
        // Smoothly simulate 10% -> 92% over 38 seconds (typical Render cold-start duration)
        const computedProgress = Math.min(92, Math.round(10 + (next / 38) * 82));
        setProgress(computedProgress);

        if (next >= 85) {
          setIsError(true);
          setStatusText("Server wakeup is taking longer than usual.");
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isWakingUp, isServerReady]);

  // Polling loop to ping /health every 3.5 seconds while waking up
  useEffect(() => {
    if (!isWakingUp || isServerReady) return;

    let isSubscribed = true;

    const poll = async () => {
      const awake = await checkServerHealth(3500);
      if (awake && isSubscribed) {
        setProgress(100);
        setStatusText("Server is online & ready!");
        setIsServerReady(true);
        setIsWakingUp(false);

        // Allow user to see the 100% completion checkmark for 1.4s before fading out
        setTimeout(() => {
          if (isSubscribed) {
            setShowNotification(false);
          }
        }, 1400);
      }
    };

    const pollInterval = setInterval(poll, 3500);
    // Trigger first poll shortly after reveal
    const initialTimeout = setTimeout(poll, 2000);

    return () => {
      isSubscribed = false;
      clearInterval(pollInterval);
      clearTimeout(initialTimeout);
    };
  }, [isWakingUp, isServerReady]);

  return (
    <ServerWarmupContext.Provider
      value={{
        isServerReady,
        isWakingUp,
        retryWarmup: startWarmup,
      }}
    >
      {children}

      {/* Floating Cold-Start Status Card */}
      {showNotification && (
        <aside
          aria-label="Server status"
          className="fixed bottom-6 right-6 z-50 max-w-md w-[calc(100vw-3rem)] pointer-events-auto animate-in fade-in slide-in-from-bottom-5 duration-300"
        >
          <div className="bg-[#131A28] border border-[#2A3346] rounded-2xl shadow-2xl p-5 text-white backdrop-blur-md">
            {/* Header row */}
            <div className="flex items-start gap-3.5 mb-3">
              <div
                className={`p-2.5 rounded-xl shrink-0 flex items-center justify-center ${
                  isServerReady
                    ? "bg-emerald-500/20 text-emerald-400"
                    : isError
                    ? "bg-rose-500/20 text-rose-400"
                    : "bg-[#F2661F]/20 text-[#F2661F]"
                }`}
              >
                {isServerReady ? (
                  <CheckCircle2 className="w-5 h-5 animate-bounce" />
                ) : isError ? (
                  <AlertCircle className="w-5 h-5" />
                ) : (
                  <CloudLightning className="w-5 h-5 animate-pulse" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-white flex items-center gap-1.5">
                    {isServerReady ? (
                      "Server Connected"
                    ) : (
                      <>
                        <span className="inline-block animate-pulse">⚡</span> {statusText}
                      </>
                    )}
                  </h4>
                  <span className="text-[11px] font-mono text-zinc-400">
                    {isServerReady ? "100%" : `${progress}%`}
                  </span>
                </div>
                <p className="text-xs text-zinc-300 mt-1 leading-relaxed">
                  {isServerReady
                    ? "Backend container is active and accepting requests."
                    : isError
                    ? "Render service is taking longer than expected. Please check your connection."
                    : "Free-tier instance is spinning up (takes ~30–40s). Please wait a moment..."}
                </p>
              </div>
            </div>

            {/* Smooth Progress Bar */}
            <div className="w-full bg-[#1B2333] h-2 rounded-full overflow-hidden mb-3 border border-[#2A3346]/60">
              <div
                className={`h-full transition-all duration-700 ease-out rounded-full ${
                  isServerReady
                    ? "bg-emerald-500"
                    : isError
                    ? "bg-rose-500"
                    : "bg-gradient-to-r from-[#F2661F] to-amber-400"
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Footer metrics / Retry button */}
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <div className="flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-zinc-500" />
                <span>Render Free Tier</span>
                <span className="text-zinc-600">•</span>
                <span>Elapsed: {elapsedSeconds}s</span>
              </div>

              {isError ? (
                <button
                  type="button"
                  onClick={startWarmup}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-white/10 hover:bg-white/20 text-white font-medium transition cursor-pointer text-xs"
                >
                  <RefreshCw className="w-3 h-3" /> Retry
                </button>
              ) : (
                <span className="text-zinc-500">
                  {isServerReady ? "Ready to submit" : "Spinning up container..."}
                </span>
              )}
            </div>
          </div>
        </aside>
      )}
    </ServerWarmupContext.Provider>
  );
}
