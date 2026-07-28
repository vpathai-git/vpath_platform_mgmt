import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/providers";
import { DemoBanner, isDemoMode, THEME_INIT_SCRIPT, VpathUpdatePrompt } from "@vpath/sdk";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

// Title/icon for the platform activity bar come from vpath-app.yaml spec.ui —
// this metadata is the document <title> only. Apps render ZERO header chrome.
export const metadata: Metadata = {
  title: "Fortune Teller",
  description: "Ask the oracle a question and receive a deterministic fortune.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Honor the platform theme before first paint (CLAUDE.md §4). */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className={`${inter.className}${isDemoMode() ? " pb-12" : ""}`}>
        <Providers>
          <main className="max-w-5xl mx-auto px-6 py-6 h-full overflow-auto">
            {children}
          </main>
        </Providers>
        <DemoBanner />
        <VpathUpdatePrompt />
      </body>
    </html>
  );
}
