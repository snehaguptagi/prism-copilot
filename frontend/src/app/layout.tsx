import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Typography is Helvetica Neue first, as PwC's own system specifies. It is a
// licensed face that cannot be embedded or served, so the stack in globals.css
// asks for the locally installed copy and falls back. On macOS that means real
// Helvetica Neue; on Windows, where it is not installed, Inter carries it as the
// closest openly-licensed neo-grotesque and is far better hinted at UI sizes
// than the Segoe UI fallback this replaces.
//
// Loaded as the VARIABLE cut (no `weight` array) so the type scale can ask for
// weights between the named stops instead of snapping to the nearest static one.
const grotesk = Inter({
  variable: "--font-grotesk",
  subsets: ["latin"],
});

// Used for tickers, ISINs and holding ids, where character-cell alignment
// genuinely helps. Display figures do not use it: they are set in the grotesk,
// whose tabular figures already cover column alignment.
const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "PRISM · PwC Portfolio Intelligence",
  description: "PwC portfolio intelligence workspace for client onboarding, portfolio oversight, and product fit.",
  openGraph: {
    title: "PRISM · PwC Portfolio Intelligence",
    description: "Portfolio intelligence for every client.",
    type: "website",
    images: [{ url: "/og.png", width: 1736, height: 909, alt: "PRISM portfolio intelligence dashboard" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "PRISM · PwC Portfolio Intelligence",
    description: "Portfolio intelligence for every client.",
    images: ["/og.png"],
  },
};

// Sets data-theme on <html> before first paint (localStorage choice, else dark),
// so there is never a flash of the wrong theme. Dark is the default rather than
// the OS preference because the design system is built dark-first and that is
// the look the product is presented in; the toggle still overrides it.
const THEME_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem('prism_theme');document.documentElement.setAttribute('data-theme',(s==='light'||s==='dark')?s:'dark');}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${grotesk.variable} ${ibmPlexMono.variable}`}
    >
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
