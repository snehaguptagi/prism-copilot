// Returns-by-horizon mini bar chart: a book's return vs its benchmark at each
// horizon (YTD / 1Y / 3Y), scaled to the tallest bar. Real computed numbers,
// not a fabricated time series. Shared by the Overview and client detail pages.
export default function PerfHorizons({
  horizons,
  benchmarkName,
}: {
  horizons: { label: string; book: number; benchmark: number | null }[];
  benchmarkName: string;
}) {
  if (!horizons.length) return null;
  const max = Math.max(...horizons.flatMap((h) => [h.book, h.benchmark ?? 0]), 1);
  return (
    <div className="perf-horizons">
      <div className="perf-horizons-chart">
        {horizons.map((h) => (
          <div className="perf-h" key={h.label}>
            <div className="perf-h-bars">
              <span
                className="perf-h-bar book"
                style={{ height: `${(h.book / max) * 100}%` }}
                title={`Book, ${h.label}: ${h.book}%`}
              />
              <span
                className="perf-h-bar bench"
                style={{ height: `${((h.benchmark ?? 0) / max) * 100}%` }}
                title={`${benchmarkName}, ${h.label}: ${h.benchmark}%`}
              />
            </div>
            <div className="perf-h-label">{h.label}</div>
            <div className="perf-h-val" style={{ color: h.book >= 0 ? "var(--positive)" : "var(--negative)" }}>
              {h.book >= 0 ? "+" : ""}
              {h.book}%
            </div>
          </div>
        ))}
      </div>
      <div className="perf-horizons-legend">
        <span>
          <span className="dot" style={{ background: "var(--accent)" }} />
          This book
        </span>
        <span>
          <span className="dot" style={{ background: "var(--text-faint)" }} />
          {benchmarkName}
        </span>
      </div>
    </div>
  );
}
