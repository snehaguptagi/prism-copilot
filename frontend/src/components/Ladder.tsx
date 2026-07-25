import { Portfolio } from "@/lib/types";
import { severityColor, severityScore } from "@/lib/colors";

export default function Ladder({ portfolios }: { portfolios: Portfolio[] }) {
  return (
    <div className="list-panel">
      {portfolios.map((p) => {
        const color = severityColor(p.risk_tier);
        const score = severityScore(p.risk_tier);
        return (
          <div className="rung" key={p.portfolio_id}>
            <div>
              <div className="pf">{p.name}</div>
              <div className="drv">
                {p.manager_name ?? "n/a"} · {p.risk_driver}
              </div>
            </div>
            <div className="rail">
              <div className="fill" style={{ width: `${score}%`, background: color }} />
            </div>
            <div className="sc">
              <span className="chip" style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}>
                <span className="chip-dot" />
                {p.risk_tier ?? "n/a"}
              </span>
              <div className="v" style={{ color, marginTop: 4 }}>
                {p.est_vol != null ? `${p.est_vol}%` : "n/a"}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
