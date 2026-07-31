import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Typography is Helvetica Neue first, as PwC's own system specifies. It is a
// licensed Linotype/Apple face that cannot be embedded or served, so the stack in
// globals.css asks for the locally installed copy and falls back. On macOS and iOS
// that means real Helvetica Neue. On Windows and Android, where it is not
// installed, Inter carries it — the closest openly-licensed neo-grotesque in
// proportion and skeleton, and better hinted at UI sizes than Arial.
//
// Loaded as the VARIABLE cut (no `weight` array) so the display scale can ask for
// weights between the named stops instead of snapping to the nearest static one.
const grotesk = Inter({
  variable: "--font-grotesk",
  subsets: ["latin"],
});

// Retained for tickers, ISINs and holding ids, where character-cell alignment
// genuinely helps. Display figures do NOT use it: the deck sets its big numbers
// in the grotesk at a light weight, and Inter's tabular figures cover alignment.
const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Client Impact Copilot · What today's markets mean for each of your clients",
  description: "Portfolio-aware research assistant for buy-side investment teams.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // Dark only. data-theme is set statically here rather than by a pre-paint
    // script, so there is no theme to detect, persist or flash — and no toggle.
    // colorScheme: dark in globals.css makes native controls (scrollbars, form
    // widgets, autofill) match, which is the part people usually forget.
    <html
      lang="en"
      data-theme="dark"
      className={`${grotesk.variable} ${ibmPlexMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
