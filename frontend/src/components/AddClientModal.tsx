"use client";

import { useState } from "react";
import { addClient } from "@/lib/api";
import { ClientAccount } from "@/lib/types";

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
        </div>

        <div className="modal-footer">
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
