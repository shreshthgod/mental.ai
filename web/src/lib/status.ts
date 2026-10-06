import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export type SystemState = "checking" | "ready" | "degraded" | "unavailable";

const POLL_MS = 30_000;

/**
 * Live system status from the real backend - /health + /ready.
 * Never hardcoded; polls on an interval while mounted.
 */
export function useSystemStatus(): SystemState {
  const [state, setState] = useState<SystemState>("checking");

  const check = useCallback(async () => {
    try {
      const h = await api.health();
      if (!h.artifacts_ok || !h.screener_available) {
        setState("degraded");
        return;
      }
      try {
        await api.ready();
        setState("ready");
      } catch {
        setState("degraded");
      }
    } catch {
      setState("unavailable");
    }
  }, []);

  useEffect(() => {
    void check();
    const id = setInterval(() => void check(), POLL_MS);
    return () => clearInterval(id);
  }, [check]);

  return state;
}
