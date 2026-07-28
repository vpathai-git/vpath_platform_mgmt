import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { DemoBanner, isDemoMode, THEME_INIT_SCRIPT, VpathUpdatePrompt } from "@vpath/sdk";
import { Providers } from "@/components/providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Storage Demo",
  description: "Browse the storage folders this app declares in its manifest.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className={`${inter.className}${isDemoMode() ? " pb-12" : ""}`}>
        <Providers>
          <main className="mx-auto h-full max-w-5xl overflow-auto px-6 py-6">
            {children}
          </main>
        </Providers>
        <DemoBanner />
        <VpathUpdatePrompt />
      </body>
    </html>
  );
}
