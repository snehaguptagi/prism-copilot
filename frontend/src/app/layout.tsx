import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// PwC's identity is single-family and strictly sans: Helvetica Neue, set bold and
// black for headlines with orange as the only accent. Inter is the substitute —
// the closest openly-licensed neo-grotesque to Helvetica in proportion and
// skeleton, and far better hinted at UI sizes.
//
// The serif italic that was here previously came from the Perplexity deck, whose
// whole typographic idea is a grotesk/serif pairing. PwC has no serif in its
// system, so keeping that flourish would have read as two brands arguing. It is
// removed rather than recoloured.
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
  title: "PRISM · Investment Research & Portfolio Insight Copilot",
  description: "Portfolio-aware research assistant for buy-side investment teams.",
};

// Sets data-theme on <html> before first paint (localStorage choice, else the
// OS preference), so there is never a flash of the wrong theme. A manual
// toggle (ThemeToggle) always overrides the OS preference once set.
const THEME_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem('prism_theme');var t=(s==='light'||s==='dark')?s:(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${grotesk.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
