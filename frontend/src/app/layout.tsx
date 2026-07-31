import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en" suppressHydrationWarning>
      <body>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
