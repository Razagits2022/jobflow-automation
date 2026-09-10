"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
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

/**
 * ServerWarmupProvider silently pings the backend health endpoint
 * in the background without rendering any floating UI widgets or popups.
 */
export function ServerWarmupProvider({ children }: { children: React.ReactNode }) {
  const [isServerReady, setIsServerReady] = useState(false);
  const [isWakingUp, setIsWakingUp] = useState(false);

  const startWarmup = async () => {
    try {
      const ready = await checkServerHealth(3000);
      setIsServerReady(ready);
      setIsWakingUp(!ready);
    } catch {
      setIsServerReady(false);
    }
  };

  useEffect(() => {
    startWarmup();
  }, []);

  return (
    <ServerWarmupContext.Provider
      value={{
        isServerReady,
        isWakingUp,
        retryWarmup: startWarmup,
      }}
    >
      {children}
    </ServerWarmupContext.Provider>
  );
}
