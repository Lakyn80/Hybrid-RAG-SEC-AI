import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";

import { UiLocaleProvider } from "@/components/UiLocaleProvider";
import { copy } from "@/lib/i18n";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin", "cyrillic"],
  variable: "--font-space-grotesk",
  weight: ["400", "500", "600", "700"],
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-ibm-plex-mono",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: copy.metadata.title,
  description: copy.metadata.description,
  icons: {
    icon: "/icon-512x512.png",
    apple: "/icon-512x512.png",
    shortcut: "/icon-512x512.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang={copy.metadata.lang}>
      <body className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}>
        <UiLocaleProvider>{children}</UiLocaleProvider>
      </body>
    </html>
  );
}
