import { EmptyState } from "@/components/ui/states";

export default function KnowledgePage() {
  return (
    <section className="page">
      <header className="page-header">
        <h2>Knowledge</h2>
        <p>Knowledge page skeleton with reserved graph area.</p>
      </header>
      <EmptyState message="Graph view and node details will be implemented later." />
    </section>
  );
}
