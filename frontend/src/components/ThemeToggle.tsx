"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "prism_theme";

export default function ThemeToggle() {
  // Mirrors whatever the boot script (layout.tsx) already set on <html>, so
  // this never causes a flash or a hydration mismatch on the icon itself.
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private browsing / storage disabled: theme still applies this session */
    }
  }

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      aria-label="Toggle light and dark theme"
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
