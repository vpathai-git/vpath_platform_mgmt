import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/providers";
import { ToastProvider } from "@/components/ToastProvider";
import { THEME_INIT_SCRIPT, VpathUpdatePrompt } from "@vpath/sdk";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "VPATH Explorer",
  description: "File system explorer powered by VPATH SDK",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className={inter.className}>
        <ToastProvider>
          <Providers>{children}</Providers>
        </ToastProvider>
        <VpathUpdatePrompt />
      </body>
    </html>
  );
}
