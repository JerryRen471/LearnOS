export type ToastItem = {
  id: string;
  title: string;
  detail: string;
  variant: "danger" | "warn" | "info";
};

type Listener = (toasts: ToastItem[]) => void;

let toasts: ToastItem[] = [];
let listeners: Listener[] = [];
let lastDedupe = { key: "", at: 0 };

function notify() {
  listeners.forEach((fn) => fn([...toasts]));
}

export function subscribeToasts(fn: Listener): () => void {
  listeners.push(fn);
  fn([...toasts]);
  return () => {
    listeners = listeners.filter((l) => l !== fn);
  };
}

export function showToast(payload: {
  title: string;
  detail: string;
  variant?: "danger" | "warn" | "info";
  dedupeMs?: number;
}): void {
  const variant = payload.variant ?? "danger";
  const key = `${variant}:${payload.title}:${payload.detail}`;
  const now = Date.now();
  const windowMs = payload.dedupeMs ?? 2500;
  if (key === lastDedupe.key && now - lastDedupe.at < windowMs) {
    return;
  }
  lastDedupe = { key, at: now };

  const id = `toast-${now}-${Math.random().toString(36).slice(2, 8)}`;
  toasts = [...toasts, { id, title: payload.title, detail: payload.detail, variant }].slice(-5);
  notify();
}

export function dismissToast(id: string): void {
  toasts = toasts.filter((t) => t.id !== id);
  notify();
}
