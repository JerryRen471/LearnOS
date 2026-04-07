import { EmptyState } from "@/components/ui/states";

export default function SettingsPage() {
  return (
    <section className="page">
      <header className="page-header">
        <h2>Settings</h2>
        <p>Global settings page skeleton.</p>
      </header>
      <EmptyState message="Settings controls are not implemented yet." />
    </section>
  );
}
