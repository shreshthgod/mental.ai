const GLYPHS = ["M", "E", "N", "T", "A", "L", ".", "A", "I"];



function pose(i: number) {
  const mid = (GLYPHS.length - 1) / 2;
  return {
    dx: `${(i - mid) * -0.05}em`,
    dy: `${(i - mid) * 0.16 + 0.3}em`,
    rot: `${(i % 2 === 0 ? 1 : -1) * (3 + i)}deg`,
    delay: 150 + i * 85,
  };
}

interface Props {
  live: boolean;
  instant?: boolean;
  plane: "back" | "front";
  dimmed?: boolean;
}

export function WordPlane({ live, instant = false, plane, dimmed = false }: Props) {
  return (
    <div
      className={`entry__word-plane entry__word-plane--${plane} ${
        dimmed ? "entry__word-plane--dim" : ""
      }`}
      aria-hidden="true"
    >
      <span className="entry__word">
        {GLYPHS.map((ch, i) => {
          const p = pose(i);
          const isDot = ch === ".";
          // Keep both planes metrically aligned, but paint every glyph above the sculpture.
          const suppressed = plane === "back";
          return (
            <span
              key={i}
              className={`entry__letter ${isDot ? "entry__letter--dot" : ""} ${
                live ? "entry__letter--in" : ""
              } ${suppressed ? "entry__letter--behind" : ""}`}
              style={{
                ["--lx" as string]: p.dx,
                ["--ly" as string]: p.dy,
                ["--lr" as string]: p.rot,
                ["--ld" as string]: `${instant ? i * 28 : p.delay}ms`,
              }}
            >
              {ch}
            </span>
          );
        })}
      </span>
    </div>
  );
}