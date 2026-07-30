"use client";

import { useEffect, useState } from "react";
import { getProfileOptions, updateProfile } from "@/lib/api";
import { ProfileOptions, Psychographics } from "@/lib/types";

const LABELS: Record<keyof Psychographics, string> = {
  primary_goal: "Primary goal",
  time_horizon: "Time horizon",
  loss_aversion: "Loss aversion",
  life_stage: "Life stage",
  decision_style: "Decision style",
  financial_literacy: "Financial literacy",
  engagement: "Engagement",
  comms_pref: "Prefers",
};

/**
 * Fills in or corrects a client's behavioral profile. Works for seeded demo
 * clients as well as ones added by hand, because the edit lands in the overlay
 * and never rewrites prism_data.json.
 *
 * The fields the backend reports as `scoring_fields` are the ones Product Fit
 * actually ranks on; the rest are descriptive. That distinction is shown rather
 * than hidden, so it is obvious which answers change the recommendations.
 */
export default function ProfileEditor({
  portfolioId,
  persona,
  psychographics,
  onSaved,
  onCancel,
}: {
  portfolioId: string;
  persona: string;
  psychographics?: Psychographics;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [options, setOptions] = useState<ProfileOptions | null>(null);
  const [psy, setPsy] = useState<Psychographics>(psychographics ?? {});
  const [personaText, setPersonaText] = useState(persona ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfileOptions().then(setOptions).catch((e) => setError(String(e)));
  }, []);

  function set(field: keyof Psychographics, value: string) {
    setPsy((prev) => {
      const next = { ...prev };
      if (value) next[field] = value;
      else delete next[field];
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await updateProfile(portfolioId, {
        persona: personaText.trim() || undefined,
        psychographics: Object.keys(psy).length ? psy : undefined,
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  if (!options) {
    return (
      <div className="panel fade-in">
        <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
          {error ?? "Loading profile options…"}
        </p>
      </div>
    );
  }

  const scoring = options.scoring_fields;
  const descriptive = (Object.keys(LABELS) as (keyof Psychographics)[]).filter(
    (f) => !scoring.includes(f),
  );

  return (
    <div className="panel fade-in">
      <div className="panel-title">Edit profile</div>

      {error && (
        <div className="panel" style={{ borderLeft: "3px solid var(--negative)", marginBottom: 12 }}>
          <p style={{ color: "var(--negative)", fontSize: 13 }}>{error}</p>
        </div>
      )}

      <label className="form-field" style={{ marginBottom: 16 }}>
        <span>Who they are</span>
        <textarea
          className="text-input"
          rows={3}
          value={personaText}
          onChange={(e) => setPersonaText(e.target.value)}
          placeholder="What you know about how this client thinks about their money."
          style={{ resize: "vertical", fontFamily: "inherit" }}
        />
      </label>

      <div className="form-divider">
        <span>Preferences that drive Product Fit</span>
        <em>ranks suggestions</em>
      </div>
      <div className="form-grid" style={{ marginBottom: 18 }}>
        {scoring.map((field) => (
          <label
            key={field}
            className="form-field"
            style={field === "primary_goal" ? { gridColumn: "1 / -1" } : undefined}
          >
            <span>{LABELS[field]}</span>
            <div className="select-wrap">
              <select value={psy[field] ?? ""} onChange={(e) => set(field, e.target.value)}>
                <option value="">Not known yet</option>
                {(options.options[field] ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
                {/* Seeded clients carry richer free-text phrasings than the
                    dropdown offers; keep the current value selectable so
                    opening this form can never silently discard it. */}
                {psy[field] && !(options.options[field] ?? []).includes(psy[field]!) && (
                  <option value={psy[field]}>{psy[field]} (current)</option>
                )}
              </select>
            </div>
          </label>
        ))}
      </div>

      <div className="form-divider">
        <span>How to work with them</span>
        <em>descriptive only</em>
      </div>
      <div className="form-grid">
        {descriptive.map((field) => (
          <label key={field} className="form-field">
            <span>{LABELS[field]}</span>
            <div className="select-wrap">
              <select value={psy[field] ?? ""} onChange={(e) => set(field, e.target.value)}>
                <option value="">Not known yet</option>
                {(options.options[field] ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
                {psy[field] && !(options.options[field] ?? []).includes(psy[field]!) && (
                  <option value={psy[field]}>{psy[field]} (current)</option>
                )}
              </select>
            </div>
          </label>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          gap: 10,
          justifyContent: "flex-end",
          marginTop: 18,
          paddingTop: 14,
          borderTop: "1px solid var(--border)",
        }}
      >
        <button className="btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button className="btn" onClick={save} disabled={saving}>
          {saving && <span className="spinner" />}
          {saving ? "Saving…" : "Save profile"}
        </button>
      </div>
    </div>
  );
}
