import type { Metadata } from "next";
import { Manrope, Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-client";
import { ServerWarmupProvider } from "@/components/ServerWarmup";
import { AccessGuard } from "@/components/AccessGuard";
import { BRAND_NAME, BRAND_TAGLINE } from "@/lib/brand";

const manrope = Manrope({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["700", "800"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: `${BRAND_NAME} — ${BRAND_TAGLINE}`,
  description:
    "JobFlow reads each posting, fills the application, and submits it for you. You add a link, it does the rest.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${inter.variable} h-full antialiased`}
    >
      <body
        className="min-h-full flex flex-col font-sans bg-canvas text-ink selection:bg-accent selection:text-white"
        suppressHydrationWarning
      >
        <QueryProvider>
          <ServerWarmupProvider>
            <AccessGuard>{children}</AccessGuard>
          </ServerWarmupProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
