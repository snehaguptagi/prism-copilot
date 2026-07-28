const ICONS: Record<string, React.ReactNode> = {
  "Global cues for India": (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" />
    </>
  ),
  "India Markets": (
    <>
      <path d="M4 19h16" />
      <path d="M6 16l4-5 3 3 5-7" />
      <path d="M18 7h1.5v1.5" />
    </>
  ),
  "India Startups": (
    <>
      <path d="M12 3c3 2 4.5 5 4.5 8 0 2-1 3.5-1 3.5H8.5S7.5 13 7.5 11c0-3 1.5-6 4.5-8Z" />
      <circle cx="12" cy="9.5" r="1.4" />
      <path d="M9.5 15l-1.5 3M14.5 15l1.5 3M12 15v4" />
    </>
  ),
  "India Politics": (
    <>
      <path d="M4 20h16M5 20V10M19 20V10M12 4l7 4H5l7-4Z" />
      <path d="M8.5 20V13M12 20V13M15.5 20V13" />
    </>
  ),
};

export default function CategoryIcon({ category, size = 20 }: { category: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {ICONS[category] ?? <circle cx="12" cy="12" r="9" />}
    </svg>
  );
}
