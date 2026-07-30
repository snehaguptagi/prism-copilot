"use client";

import { useEffect, useState } from "react";
import { addClient, getProfileOptions } from "@/lib/api";
import { ClientAccount, ProfileOptions, Psychographics } from "@/lib/types";

// Every mandate string the backend's suitability check recognizes
// (_MANDATE_MAX_TIER / _MANDATE_MIN_TIER in api.py). Keep in sync with those.
const RISK_MANDATES = [
  "Conservative",
  "Conservative-Income",
  "Conservative-Moderate",
  "Conservative-Growth",
  "Moderate",
  "Moderate-Income",
  "Moderate-Passive",
  "Moderate-Growth",
  "Growth",
  "Growth-Stable",
  "Growth-Concentrated",
  "Balanced-Diversified",
  "Aggressive",
  "Aggressive-Growth",
  "Aggressive-Concentrated",
];

export default function AddClientModal({
  templates,
  onClose,
  onCreated,
}: {
  templates: ClientAccount[];
  onClose: () => void;
  onCreated: (portfolioId: string) => void;
}) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [occupation, setOccupation] = useState("");
  const [city, setCity] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [mandate, setMandate] = useState("Moderate");
  const [aum, setAum] = useState("5000000");
  const [templateId, setTemplateId] = useState(templates[0]?.portfolio_id ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The four preference fields that drive Product Fit. Optional here (you often
  // don't know them on day one) but offered up front, because without them the
  // recommender has nothing to match on and can only fall back to gap-filling.
  const [profileOptions, setProfileOptions] = useState<ProfileOptions | null>(null);
  const [psy, setPsy] = useState<Psychographics>({});

  useEffect(() => {
    getProfileOptions().then(setProfileOptions).catch(() => setProfileOptions(null));
  }, []);

  function setPref(field: keyof Psychographics, value: string) {
    setPsy((prev) => {
      const next = { ...prev };
      if (value) next[field] = value;
      else delete next[field];
      return next;
    });
  }

  const prefsGiven = Object.keys(psy).length;

  async function submit() {
    if (!name.trim() || !occupation.trim() || !city.trim() || !templateId) {
      setError("Name, occupation, city, and a starting strategy are required.");
      return;
    }
    const aumNum = Number(aum);
    if (!aumNum || aumNum <= 0) {
      setError("Enter a valid initial AUM greater than zero.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await addClient({
        name: name.trim(),
        occupation: occupation.trim(),
        city: city.trim(),
        risk_mandate: mandate,
        initial_aum: aumNum,
        template_portfolio_id: templateId,
        age: age ? Number(age) : undefined,
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        psychographics: prefsGiven ? psy : undefined,
      });
      onCreated(result.portfolio_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">Add a client</div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="panel" style={{ borderLeft: "3px solid var(--negative)", marginBottom: 12 }}>
              <p style={{ color: "var(--negative)", fontSize: 13 }}>{error}</p>
            </div>
          )}

          <p style={{ fontSize: 12.5, color: "var(--text-faint)", marginBottom: 14 }}>
            Picks a starting portfolio allocation from an existing strategy, scaled to this client&apos;s AUM.
            Behavioral profile and communication history can be added later as you learn more about them.
          </p>

          <div className="form-grid">
            <label className="form-field">
              <span>Name</span>
              <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Client's full name" />
            </label>
            <label className="form-field">
              <span>Age</span>
              <input className="text-input" type="number" value={age} onChange={(e) => setAge(e.target.value)} placeholder="Optional" />
            </label>
            <label className="form-field">
              <span>Occupation</span>
              <input
                className="text-input"
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                placeholder="e.g. Senior product manager"
              />
            </label>
            <label className="form-field">
              <span>City</span>
              <input className="text-input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="e.g. Mumbai" />
            </label>
            <label className="form-field">
              <span>Email</span>
              <input className="text-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Optional" />
            </label>
            <label className="form-field">
              <span>Phone</span>
              <input className="text-input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Optional" />
            </label>
            <label className="form-field">
              <span>Risk mandate</span>
              <div className="select-wrap">
                <select value={mandate} onChange={(e) => setMandate(e.target.value)}>
                  {RISK_MANDATES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </label>
            <label className="form-field">
              <span>Initial AUM (₹)</span>
              <input className="text-input" type="number" value={aum} onChange={(e) => setAum(e.target.value)} placeholder="e.g. 5000000" />
            </label>
            <label className="form-field" style={{ gridColumn: "1 / -1" }}>
              <span>Starting strategy</span>
              <div className="select-wrap">
                <select value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
                  {templates.map((t) => (
                    <option key={t.portfolio_id} value={t.portfolio_id}>
                      {t.portfolio_name} (modeled on {t.client.name}&apos;s book)
                    </option>
                  ))}
                </select>
              </div>
            </label>
          </div>

          {profileOptions && (
            <>
              <div className="form-divider">
                <span>What they care about</span>
                <em>optional</em>
              </div>
              <p style={{ fontSize: 12.5, color: "var(--text-faint)", marginBottom: 14 }}>
                These four answers are what Product Fit matches products against. Leave them blank and
                the client still works everywhere, but suggestions can only fall back to filling
                allocation gaps. You can fill them in later from the client&apos;s Profile tab.
              </p>
              <div className="form-grid">
                <PrefField
                  label="Primary goal"
                  field="primary_goal"
                  options={profileOptions.options.primary_goal}
                  value={psy.primary_goal}
                  onChange={setPref}
                  wide
                />
                <PrefField
                  label="Time horizon"
                  field="time_horizon"
                  options={profileOptions.options.time_horizon}
                  value={psy.time_horizon}
                  onChange={setPref}
                />
                <PrefField
                  label="Loss aversion"
                  field="loss_aversion"
                  options={profileOptions.options.loss_aversion}
                  value={psy.loss_aversion}
                  onChange={setPref}
                />
                <PrefField
                  label="Life stage"
                  field="life_stage"
                  options={profileOptions.options.life_stage}
                  value={psy.life_stage}
                  onChange={setPref}
                />
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          <span style={{ marginRight: "auto", fontSize: 12, color: "var(--text-faint)" }}>
            {prefsGiven === 4
              ? "Full preference profile — Product Fit will rank on it"
              : `${prefsGiven} of 4 preferences set`}
          </span>
          <button className="btn-secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button className="btn" onClick={submit} disabled={submitting}>
            {submitting && <span className="spinner" />}
            {submitting ? "Adding…" : "Add client"}
          </button>
        </div>
      </div>
    </div>
  );
}

function PrefField({
  label,
  field,
  options,
  value,
  onChange,
  wide,
}: {
  label: string;
  field: keyof Psychographics;
  options: string[];
  value?: string;
  onChange: (field: keyof Psychographics, value: string) => void;
  wide?: boolean;
}) {
  return (
    <label className="form-field" style={wide ? { gridColumn: "1 / -1" } : undefined}>
      <span>{label}</span>
      <div className="select-wrap">
        <select value={value ?? ""} onChange={(e) => onChange(field, e.target.value)}>
          <option value="">Not known yet</option>
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </div>
    </label>
  );
}
