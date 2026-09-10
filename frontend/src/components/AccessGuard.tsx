"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { hasValidAccess } from "@/lib/access-code";
import { Logo } from "@/components/ui/Logo";
import { Lock } from "lucide-react";

const UNGUARDED_PATHS = ["/accesscode", "/acesscode"];

export function AccessGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [hasChecked, setHasChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const isUnguarded = UNGUARDED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );

  useEffect(() => {
    const checkAccess = () => {
      const valid = hasValidAccess();
      setAuthenticated(valid);
      setHasChecked(true);

      if (!valid && !isUnguarded) {
        if (pathname && pathname !== "/") {
          const returnUrl = encodeURIComponent(pathname);
          router.replace(`/accesscode?returnUrl=${returnUrl}`);
        } else {
          router.replace("/accesscode");
        }
      }
    };

    checkAccess();

    const handleAccessChange = () => checkAccess();
    window.addEventListener("jobflow-access-changed", handleAccessChange);
    window.addEventListener("storage", handleAccessChange);
    window.addEventListener("focus", handleAccessChange);
    document.addEventListener("visibilitychange", handleAccessChange);

    return () => {
      window.removeEventListener("jobflow-access-changed", handleAccessChange);
      window.removeEventListener("storage", handleAccessChange);
      window.removeEventListener("focus", handleAccessChange);
      document.removeEventListener("visibilitychange", handleAccessChange);
    };
  }, [pathname, isUnguarded, router]);

  // If on unguarded paths (/accesscode, /acesscode), always render content
  if (isUnguarded) {
    return <>{children}</>;
  }

  // During initial client hydration, render a sleek placeholder to prevent layout flash
  if (!hasChecked) {
    return (
      <div className="min-h-screen w-full bg-canvas flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <Logo />
          <div className="flex items-center gap-2 text-xs font-semibold text-muted uppercase tracking-widest mt-2">
            <Lock className="w-3.5 h-3.5 text-accent animate-spin" />
            <span>Verifying Access Pass...</span>
          </div>
        </div>
      </div>
    );
  }

  // If not authenticated, keep showing lock placeholder while redirect finishes
  if (!authenticated) {
    return (
      <div className="min-h-screen w-full bg-canvas flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4">
          <Logo />
          <div className="flex items-center gap-2 text-xs font-semibold text-muted uppercase tracking-widest mt-2">
            <Lock className="w-3.5 h-3.5 text-accent" />
            <span>Redirecting to Access Portal...</span>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
