"use client";

import { FormEvent, useEffect, useState } from "react";
import { deleteClient } from "@/lib/api";

export default function DeleteClientModal({
  portfolioId,
  clientName,
  onClose,
  onDeleted,
}: {
  portfolioId: string;
  clientName: string;
  onClose: () => void;
  onDeleted: (portfolioId: string) => void;
}) {
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
    setSubmitting(true);
    setError(null);
    try {
      await deleteClient(portfolioId);
      onDeleted(portfolioId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to remove this client.");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onMouseDown={() => !submitting && onClose()}>
      <form
        className="modal-panel delete-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-client-title"
        onSubmit={submit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            <div className="modal-kicker">Client record</div>
            <div className="modal-title" id="delete-client-title">Remove {clientName}?</div>
          </div>
          <button className="modal-close" type="button" onClick={onClose} aria-label="Close" disabled={submitting}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="delete-warning-icon" aria-hidden="true">!</div>
          <p className="delete-warning-copy">
            This removes the client, their portfolio holdings, and calculated risk record from PRISM.
            This action cannot be undone.
          </p>
          {error && <p className="form-error" role="alert">{error}</p>}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" type="button" onClick={onClose} disabled={submitting}>
            Keep client
          </button>
          <button className="btn btn-danger" type="submit" disabled={submitting}>
            {submitting && <span className="spinner" />}
            {submitting ? "Removing…" : "Remove client"}
          </button>
        </div>
      </form>
    </div>
  );
}
