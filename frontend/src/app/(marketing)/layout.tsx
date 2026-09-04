import React from "react";
import { MarketingNav } from "./MarketingNav";
import { MarketingFooter } from "./MarketingFooter";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full bg-canvas flex flex-col justify-between">
      <MarketingNav />
      <main className="flex-1 w-full">{children}</main>
      <MarketingFooter />
    </div>
  );
}
