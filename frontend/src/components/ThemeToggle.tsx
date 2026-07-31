"use client";

const STORAGE_KEY = "prism_theme";

export default function ThemeToggle() {
  function toggle() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
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
      title="Switch colour theme"
      aria-label="Toggle light and dark theme"
    >
      <span className="theme-icon theme-icon-light" aria-hidden="true">☀</span>
      <span className="theme-icon theme-icon-dark" aria-hidden="true">☾</span>
    </button>
  );
}
