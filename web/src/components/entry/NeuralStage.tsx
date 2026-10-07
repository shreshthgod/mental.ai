/**
 * WebGL host for the entry sculpture.
 *
 * Three tiers of degradation, so a missing or broken GPU never costs the user
 * the login form: the WebGL sculpture, then the existing 2D canvas signal
 * structure, then whatever CSS is behind the canvas either way. The fallback
 * path is the same engine the About hero already uses, so there is no second
 * 2D implementation to maintain.
 *
 * Placement is passed to both engines as fractions of the canvas box. The canvas
 * is the visual stage - a grid column, not the window - so the form is
 * composed into that box and re-framed whenever the column changes width,
 * instead of being positioned against the viewport.
 */
import { useEffect, useRef } from "react";
import { createNeuralSculpture } from "../hero/neural";
import { createSignalStructure } from "../hero/engine";
import { useReducedMotion } from "../../lib/motion";

interface Props {
  /** ms before the metal starts materializing out of darkness. */
  emergeDelayMs?: number;
  /** 0..1, how far the form has contracted toward the centre. */
  focus?: number;
  /**
   * Centre of the form's visual mass as a fraction of the stage, plus a size
   * multiplier. Defaults place it left of centre and above the midpoint, which
   * is where the wordmark and the hero copy leave it room.
   */
  framing?: { x?: number; y?: number; scale?: number };
  className?: string;
}

interface Handle {
  start(): void;
  stop(): void;
  destroy(): void;
  setPointer(x: number, y: number): void;
  setFocus?(v: number): void;
}

const FRAMING = { x: 0.5, y: 0.4, scale: 1 };

export default function NeuralStage({
  emergeDelayMs = 0,
  focus = 0,
  framing = FRAMING,
  className,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<Handle | null>(null);
  const reduced = useReducedMotion();
  const focusRef = useRef(focus);
  focusRef.current = focus;
  // Captured once: the framing describes the composition and does not change
  // over the life of the canvas, and re-running the effect on prop identity
  // would tear down the GL context.
  const framingRef = useRef(framing);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const quality = window.innerWidth < 768 ? 0.55 : 1;
    const place = framingRef.current;
    const webgl = createNeuralSculpture(canvas, {
      reducedMotion: reduced,
      emergeDelayMs,
      quality,
      framing: place,
    });
    // Recorded so a QA run can tell which tier is live; the two look nothing
    // alike and "the hero is black" is otherwise impossible to diagnose.
    canvas.dataset.engine = webgl ? "webgl" : "fallback-2d";
    const engine: Handle | null =
      webgl ?? createSignalStructure(canvas, { reducedMotion: reduced, emergeDelayMs, quality, framing: place });
    if (!engine) {
      canvas.dataset.engine = "none";
      return;
    }
    engineRef.current = engine;
    engine.start();
    return () => {
      engine.destroy();
      engineRef.current = null;
    };
  }, [reduced, emergeDelayMs]);

  // Pointer parallax, rAF-coalesced so a fast mouse cannot flood the engine.
  useEffect(() => {
    if (reduced) return;
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const nx = (e.clientX / window.innerWidth) * 2 - 1;
        const ny = (e.clientY / window.innerHeight) * 2 - 1;
        engineRef.current?.setPointer(nx, ny);
      });
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, [reduced]);

  // Driven from a ref so changing focus never tears down the GL context.
  useEffect(() => {
    engineRef.current?.setFocus?.(focusRef.current);
  }, [focus]);

  return (
    <div className={className} aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  );
}