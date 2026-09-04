/**
 * TanStack Query client + provider.
 *
 * The QueryClientProvider wraps the entire app in the root layout.
 * Import ``queryClient`` directly for imperative cache operations.
 */
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

// ---------------------------------------------------------------------------
// Singleton query client (server-side) — used for SSR prefetching
// ---------------------------------------------------------------------------
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 s before refetch
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ---------------------------------------------------------------------------
// Provider component — wrap the app once in the root layout
// ---------------------------------------------------------------------------
interface QueryProviderProps {
  children: ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
  // Create a new QueryClient per-render on the client to avoid shared state
  // between server renders (Next.js App Router pattern).
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
