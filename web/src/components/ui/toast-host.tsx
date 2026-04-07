"use client";

import { useEffect, useState } from "react";

import { dismissToast, subscribeToasts, type ToastItem } from "@/utils/toast-store";

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (!items.length) {
    return null;
  }

  return (
    <div className="toast-host" role="region" aria-label="Notifications">
      {items.map((toast) => (
        <div
          key={toast.id}
          className={`toast-item toast-${toast.variant}`}
          role="alert"
          aria-live="assertive"
        >
          <div className="toast-body">
            <strong>{toast.title}</strong>
            <p>{toast.detail}</p>
          </div>
          <button type="button" className="toast-dismiss" onClick={() => dismissToast(toast.id)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
