import type { Metadata } from "next";
import { Inter, Instrument_Serif, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Typography follows the Perplexity deck's pairing: a neutral grotesk carrying
// everything, at weights from Thin to Semibold, plus a serif italic used for
// exactly one emphasized word inside a grotesk line ("Search like *never*
// before.").
//
// The deck itself sets FK Grotesk, which is commercially licensed and cannot be
// redistributed here. Inter is the substitute: the same neo-grotesque genre
// (closed apertures, low contrast, neutral skeleton) and, critically, it ships
// the 200-300 weights the deck's display treatment depends on. Instrument Serif
// is the deck's actual accent face and is openly licensed, so that one is exact.
// Loaded as the VARIABLE font (no `weight` array) rather than a set of static
// cuts, because the display scale asks for weights between the named stops
// (--weight-display is 250). With static cuts the browser snaps to the nearest
// loaded weight and the intended thinness is lost.
const grotesk = Inter({
  variable: "--font-grotesk",
  subsets: ["latin"],
});

const serifAccent = Instrument_Serif({
  variable: "--font-serif-accent",
  subsets: ["latin"],
  weight: ["400"],
  style: ["italic"],
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
      className={`${grotesk.variable} ${serifAccent.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
