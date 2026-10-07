/**
 * Giant MENTAL.AI wordmark, split into a back and a front plane.
 *
 * The point of the composition is that the sculpture and the type occupy the
 * same space rather than the type sitting on top of a picture. So the word is
 * rendered twice at identical metrics: once beneath the WebGL canvas, and once
 * above it with only a central run of letters visible.
 *
 * The front run uses `visibility: hidden` for the letters it does not show
 * rather than removing them, which keeps both copies pixel-identical - the
 * alternative (rendering only the front letters) drifts by a fraction of a
 * pixel as the fonts settle and the intersection breaks.
 *
 * Decorative: the name is also exposed once to assistive technology.
 */
const GLYPHS = ["M", "E", "N", "T", "A", "L", ".", "A", "I"];

/** Indices drawn in front of the sculpture: the middle of the word. */
const FRONT = new Set([2, 3, 4]);

/** Scattered start pose per glyph, so the word assembles rather than fades. */
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
  instant: boolean;
  /**
   * Which plane to draw. The two are siblings in the page with the WebGL canvas
   * between them, so neither can wrap the other: a wrapper with a stacking
   * context of its own would trap both planes below or above the sculpture and
   * the intersection would be gone.
   */
  plane: "back" | "front";
  /** Dims the type during the post-login greeting. */
  dimmed?: boolean;
}

export function WordPlane({ live, instant, plane, dimmed = false }: Props) {
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
          // In the front plane only the crossing letters are painted; the rest
          // keep their box via visibility so the two planes stay aligned.
          const suppressed = plane === "front" && !FRONT.has(i);
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