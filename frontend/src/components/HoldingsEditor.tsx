"use client";

import { useEffect, useMemo, useState } from "react";
import { getSecurities, updateHoldings } from "@/lib/api";
import { ClientHolding, Security } from "@/lib/types";
import { inr } from "@/lib/format";

interface Row {
  security_id: string;
  name: string;
  ticker: string;
  weight: string; // kept as text so a half-typed "1." doesn't snap to a number
}

/**
 * Edits a client's allocation in place. The demo strategy seeds the book; this
 * is where an RM makes it theirs.
 *
 * Weights are entered as percentages but sent raw: the backend normalizes them
 * with the same formula the seed data's non-round weights go through, so the
 * total does not have to land on exactly 100. NAV is held constant, so this
 * changes how the money is allocated, never how much there is.
 */
export default function HoldingsEditor({
  portfolioId,
  holdings,
  aum,
  onSaved,
  onCancel,
}: {
  portfolioId: string;
  holdings: ClientHolding[];
  aum: number;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [rows, setRows] = useState<Row[]>(
    holdings.map((h) => ({
      security_id: h.security_id,
      name: h.name,
      ticker: h.ticker,
      weight: String(h.weight_pct),
    })),
  );
  const [universe, setUniverse] = useState<Security[]>([]);
  const [picker, setPicker] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSecurities().then(setUniverse).catch(() => setUniverse([]));
  }, []);

  const held = useMemo(() => new Set(rows.map((r) => r.security_id)), [rows]);
  const available = useMemo(
    () => universe.filter((s) => !held.has(s.security_id)),
    [universe, held],
  );

  const parsed = rows.map((r) => Number(r.weight));
  const total = parsed.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0);
  const invalid = rows.some((r) => !(Number(r.weight) > 0));

  function setWeight(securityId: string, weight: string) {
    setRows((prev) => prev.map((r) => (r.security_id === securityId ? { ...r, weight } : r)));
  }

  function remove(securityId: string) {
    setRows((prev) => prev.filter((r) => r.security_id !== securityId));
  }

  function add() {
    const sec = universe.find((s) => s.security_id === picker);
    if (!sec) return;
    setRows((prev) => [
      ...prev,
      { security_id: sec.security_id, name: sec.name, ticker: sec.ticker, weight: "5" },
    ]);
    setPicker("");
  }

  async function save() {
    if (!rows.length) {
      setError("A portfolio needs at least one holding.");
      return;
    }
    if (invalid) {
      setError("Every weight must be greater than zero. Remove a holding instead of zeroing it.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateHoldings(
        portfolioId,
        rows.map((r) => ({ security_id: r.security_id, weight: Number(r.weight) })),
      );
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel fade-in">
      <div className="panel-title">Edit holdings</div>
      <p style={{ fontSize: 12.5, color: "var(--text-faint)", marginBottom: 14 }}>
        Weights are percentages and are normalized on save, so they need not total exactly 100.
        AUM stays at {inr(aum)}; risk tier, volatility and concentration are recomputed from the new
        mix by the same formula used for every client.
      </p>

      {error && (
        <div className="panel" style={{ borderLeft: "3px solid var(--negative)", marginBottom: 12 }}>
          <p style={{ color: "var(--negative)", fontSize: 13 }}>{error}</p>
        </div>
      )}

      <div className="table-wrap" style={{ marginBottom: 14 }}>
        <table>
          <thead>
            <tr>
              <th>Holding</th>
              <th>Ticker</th>
              <th style={{ textAlign: "right", width: 130 }}>Weight %</th>
              <th style={{ textAlign: "right", width: 140 }}>Value at {inr(aum)}</th>
              <th style={{ width: 60 }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const w = Number(r.weight);
              const share = total > 0 && Number.isFinite(w) ? (w / total) * aum : 0;
              return (
                <tr key={r.security_id}>
                  <td>{r.name}</td>
                  <td>{r.ticker}</td>
                  <td style={{ textAlign: "right" }}>
                    <input
                      className="text-input"
                      type="number"
                      min="0"
                      step="0.1"
                      value={r.weight}
                      onChange={(e) => setWeight(r.security_id, e.target.value)}
                      style={{
                        width: 90,
                        textAlign: "right",
                        borderColor: w > 0 ? undefined : "var(--negative)",
                      }}
                      aria-label={`Weight for ${r.name}`}
                    />
                  </td>
                  <td className="num">{inr(share)}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      className="btn-secondary"
                      style={{ padding: "4px 10px", fontSize: 12 }}
                      onClick={() => remove(r.security_id)}
                      aria-label={`Remove ${r.name}`}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              );
            })}
            {!rows.length && (
              <tr>
                <td colSpan={5} style={{ color: "var(--text-faint)", fontSize: 13 }}>
                  No holdings. Add at least one below.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
        <label className="form-field" style={{ flex: 1, minWidth: 240 }}>
          <span>Add a security</span>
          <div className="select-wrap">
            <select value={picker} onChange={(e) => setPicker(e.target.value)}>
              <option value="">
                {available.length ? "Pick from the investable universe…" : "Everything is already held"}
              </option>
              {available.map((s) => (
                <option key={s.security_id} value={s.security_id}>
                  {s.name} ({s.ticker}) · {s.asset_class}
                </option>
              ))}
            </select>
          </div>
        </label>
        <button className="btn-secondary" onClick={add} disabled={!picker}>
          Add
        </button>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginTop: 18,
          paddingTop: 14,
          borderTop: "1px solid var(--border)",
        }}
      >
        <span style={{ fontSize: 12.5, color: "var(--text-secondary)" }}>
          {rows.length} {rows.length === 1 ? "holding" : "holdings"} · entered total{" "}
          <b style={{ color: "var(--text)" }}>{total.toFixed(1)}%</b>
          {rows.length > 0 && Math.abs(total - 100) > 0.05 && (
            <em style={{ color: "var(--text-faint)", fontStyle: "normal" }}>
              {" "}
              (normalized to 100% on save)
            </em>
          )}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
          <button className="btn-secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          <button className="btn" onClick={save} disabled={saving || !rows.length || invalid}>
            {saving && <span className="spinner" />}
            {saving ? "Saving…" : "Save holdings"}
          </button>
        </span>
      </div>
    </div>
  );
}
