import { ReactNode } from "react";

type StateCardProps = {
  title: string;
  description: string;
  tone: "info" | "success" | "warn" | "danger";
  action?: ReactNode;
};

function StateCard({ title, description, tone, action }: StateCardProps) {
  return (
    <section className={`state-card tone-${tone}`} role="status" aria-live="polite">
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="state-action">{action}</div> : null}
    </section>
  );
}

export function LoadingState({ message = "Loading data..." }: { message?: string }) {
  return <StateCard title="Loading" description={message} tone="info" />;
}

export function EmptyState({ message = "No data available." }: { message?: string }) {
  return <StateCard title="Empty" description={message} tone="warn" />;
}

export function ErrorState({ message }: { message: string }) {
  return <StateCard title="Request failed" description={message} tone="danger" />;
}

export function SuccessState({ message }: { message: string }) {
  return <StateCard title="Success" description={message} tone="success" />;
}
