import { useEffect, useRef, useState, useSyncExternalStore } from "react";

const mq = () => window.matchMedia("(prefers-reduced-motion: reduce)");

const subscribe = (cb: () => void) => {
  const m = mq();
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
};

export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => mq().matches,
    () => false
  );
}

/** Observe an element once; returns [ref, inView]. */
export function useInView<T extends HTMLElement>(threshold = 0.18) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);

  return [ref, inView] as const;
}

/** Count-up that runs once when `active` becomes true. */
export function useCountUp(target: number, active: boolean, durationMs = 1400, decimals = 0) {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (!active || started.current) return;
    started.current = true;
    if (reduced) {
      setValue(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / durationMs);
      const eased = 1 - Math.pow(1 - t, 4);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else setValue(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, durationMs, reduced]);

  return value.toFixed(decimals);
}
