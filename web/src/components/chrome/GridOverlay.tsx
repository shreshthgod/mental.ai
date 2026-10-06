/** Fixed editorial grid - hairline columns across the whole site. */
export function GridOverlay({ on }: { on: boolean }) {
  return (
    <div className={`grid-overlay ${on ? "grid-overlay--on" : ""}`} aria-hidden="true">
      <div className="grid-overlay__cols" />
    </div>
  );
}
