"use client";

import { FormEvent, useEffect, useState } from "react";
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

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !submitting) onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, submitting]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to add this client.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onMouseDown={() => !submitting && onClose()}>
      <form
        className="modal-panel add-client-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-client-title"
        onSubmit={submit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div className="modal-kicker">New relationship</div>
            <div className="modal-title" id="add-client-title">Add a client</div>
          </div>
          <button className="modal-close" type="button" onClick={onClose} aria-label="Close" disabled={submitting}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-intro">
            Create the client profile and seed a portfolio from an existing strategy. PRISM scales
            the holdings to the opening AUM and calculates the resulting risk profile automatically.
          </p>

          <div className="form-grid">
            <label className="form-field">
              <span>Name</span>
              <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Client's full name" autoFocus required />
            </label>
            <label className="form-field">
              <span>Age</span>
              <input className="text-input" type="number" min="18" max="100" value={age} onChange={(e) => setAge(e.target.value)} placeholder="Optional" />
            </label>
            <label className="form-field">
              <span>Occupation</span>
              <input
                className="text-input"
                value={occupation}
                onChange={(e) => setOccupation(e.target.value)}
                placeholder="e.g. Senior product manager"
                required
              />
            </label>
            <label className="form-field">
              <span>City</span>
              <input className="text-input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="e.g. Mumbai" required />
            </label>
            <label className="form-field">
              <span>Email</span>
              <input className="text-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" />
            </label>
            <label className="form-field">
              <span>Phone</span>
              <input className="text-input" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 98765 43210" />
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
              <input className="text-input" type="number" min="1" step="1000" value={aum} onChange={(e) => setAum(e.target.value)} placeholder="e.g. 5000000" required />
            </label>
            <label className="form-field" style={{ gridColumn: "1 / -1" }}>
              <span>Starting portfolio strategy</span>
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

          {error && <p className="form-error" role="alert">{error}</p>}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" type="button" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button className="btn" type="submit" disabled={submitting || !templateId}>
            {submitting && <span className="spinner" />}
            {submitting ? "Adding…" : "Add client"}
          </button>
        </div>
      </form>
    </div>
  );
}
