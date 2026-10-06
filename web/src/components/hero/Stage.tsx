import { useEffect, useRef } from "react";
import { createSculpture } from "./sculpture";
import { createSignalStructure, type SignalStructureHandle } from "./engine";
import { useReducedMotion } from "../../lib/motion";

interface Props {
  emergeDelayMs?: number;
  className?: string;
}

/**
 * Hero visual host. Uses the WebGL metallic sculpture when available,
 * falling back to the 2D canvas signal structure when WebGL is not.
 */
export default function Stage({ emergeDelayMs = 0, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const engineRef = useRef<SignalStructureHandle | null>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const quality = window.innerWidth < 768 ? 0.6 : 1;
    const engine =
      createSculpture(canvas, { reducedMotion: reduced, emergeDelayMs, quality }) ??
      createSignalStructure(canvas, { reducedMotion: reduced, emergeDelayMs, quality });
    engineRef.current = engine;
    engine.start();
    return () => engine.destroy();
  }, [reduced, emergeDelayMs]);

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

  return (
    <div className={className} aria-hidden="true">
      <canvas ref={canvasRef} role="img" aria-label="Abstract dark-chrome sculpture: two intertwined metallic ribbons and precision rings representing Vantage's dual-signal inference system" />
    </div>
  );
}
