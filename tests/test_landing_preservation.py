from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]


def test_original_sculpture_geometry_and_animation_are_preserved():
    source = (ROOT / "web/src/components/hero/neural.ts").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(source).hexdigest() == "f162fec33cfdcebdcc5e043085cf260902486cce12e596db0975fe88b3237aff"


def test_original_glyph_entrance_definitions_are_preserved():
    css = (ROOT / "web/src/styles/entry.css").read_text()
    assert "opacity 900ms var(--ease-out-expo)" in css
    assert "transform 1100ms var(--ease-out-expo)" in css
    assert "filter 1000ms var(--ease-out-expo)" in css
    assert "translate(var(--lx, 0), var(--ly, 0.4em)) rotate(var(--lr, 4deg)) scale(1.06)" in css
    word = (ROOT / "web/src/components/entry/Wordmark.tsx").read_text()
    assert "delay: 150 + i * 85" in word
    assert 'const suppressed = plane === "back"' in word
