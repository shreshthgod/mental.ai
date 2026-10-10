/**
 * MENTAL.AI Wordmark — Metallic Marvel / Transformers Movie Credits Style.
 *
 * Chiseled, solid metallic typography with chrome beveling, high-contrast
 * specular reflections, and cinematic 1-second lock-in animation.
 *
 * Rendered in dual planes (back and front) so the metallic DNA sculpture passes
 * directly through the letters without clipping artifacts.
 */

const GLYPHS = ["M", "E", "N", "T", "A", "L", ".", "A", "I"];

/** Indices drawn in front of the sculpture: the middle crossing letters. */
const FRONT = new Set([2, 3, 4]);

interface Props {
  live: boolean;
  instant?: boolean;
  plane: "back" | "front";
  dimmed?: boolean;
}

export function WordPlane({ live, plane, dimmed = false }: Props) {
  return (
    <div
      className={`entry__word-plane entry__word-plane--${plane} ${
        dimmed ? "entry__word-plane--dim" : ""
      }`}
      aria-hidden="true"
    >
      <span className="entry__word">
        {GLYPHS.map((ch, i) => {
          const isDot = ch === ".";
          // In front plane only crossing letters are painted; rest remain invisible to hold exact metrics
          const suppressed = plane === "front" && !FRONT.has(i);
          return (
            <span
              key={i}
              className={`entry__letter ${isDot ? "entry__letter--dot" : ""} ${
                live ? "entry__letter--in" : ""
              } ${suppressed ? "entry__letter--behind" : ""}`}
              style={{
                ["--char-index" as string]: i,
                ["--letter-delay" as string]: `${i * 85}ms`,
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