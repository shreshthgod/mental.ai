import { useEffect, useState } from "react";
import { clearCheckIn } from "../../lib/checkin";
import { clearHistory } from "../../lib/history";
import { onSessionChange } from "../../lib/auth";
import { clearAllPersonalization, loadPersonalizationPrefs, savePersonalizationPrefs } from "../../lib/personalization";

export function PersonalizationControls({ onDelete }: { onDelete: () => void }) {
  const [prefs, setPrefs] = useState(loadPersonalizationPrefs);
  useEffect(() => {
    const refresh = () => setPrefs(loadPersonalizationPrefs());
    const unsubscribe = onSessionChange(refresh);
    window.addEventListener("mental-personalization-change", refresh);
    return () => { unsubscribe(); window.removeEventListener("mental-personalization-change", refresh); };
  }, []);
  const [deletion, setDeletion] = useState("");
  return <details className="privacy-controls">
    <summary>Personalization and saved themes</summary>
    <p>Opt in to deriving and saving broad themes from future submissions on this browser for your account. Themes can reveal sensitive information. They are not uploaded and do not indicate current danger. Browser storage is not encrypted.</p>
    <label>
      <input type="checkbox" checked={prefs.enabled} onChange={e => {
        savePersonalizationPrefs({ enabled: e.target.checked });
        setPrefs(loadPersonalizationPrefs());
      }} /> Remember themes for future greetings
    </label>
    <p>Saved themes: {prefs.rememberedThemes.join(", ") || "None"}</p>
    <button className="workspace__restart" type="button" onClick={() => {
      clearAllPersonalization();
      setPrefs(loadPersonalizationPrefs());
    }}>Clear personalization and disable</button>
    <button className="workspace__restart" type="button" onClick={() => {
      clearCheckIn(); clearAllPersonalization();
      const deleted = clearHistory();
      setPrefs(loadPersonalizationPrefs());
      if (deleted) onDelete();
      setDeletion(deleted ? "Device history and personalization cleared. Account history is separate." : "Device history could not be cleared.");
    }}>Delete local history, check-in and personalization</button>
    <p role="status">{deletion}</p>
  </details>;
}
