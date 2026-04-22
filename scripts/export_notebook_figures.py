"""Extract PNG outputs from dst_crime_analysis.ipynb into figures/memo/."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "dst_crime_analysis.ipynb"
OUT_DIR = ROOT / "figures" / "memo"


def slug(s: str, max_len: int = 50) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.ASCII)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return (s[:max_len] or "figure").lower()


def main() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    last_md_heading = "intro"
    saved: list[tuple[str, str]] = []

    for ci, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "markdown":
            text = "".join(cell.get("source", []))
            m = re.search(r"^#+\s*(.+)$", text, re.MULTILINE)
            if m:
                last_md_heading = slug(m.group(1))

        if cell["cell_type"] != "code":
            continue

        src = "".join(cell.get("source", []))
        pic_idx = 0
        for o in cell.get("outputs", []):
            if o.get("output_type") != "display_data":
                continue
            data = o.get("data") or {}
            b64 = data.get("image/png")
            if not b64:
                continue
            pic_idx += 1
            raw = base64.b64decode(b64)
            fname = f"{len(saved) + 1:02d}_{last_md_heading}"
            if pic_idx > 1:
                fname += f"_part{pic_idx}"
            fname += ".png"
            path = OUT_DIR / fname
            path.write_bytes(raw)
            saved.append((fname, last_md_heading))

    manifest = OUT_DIR / "MANIFEST.txt"
    manifest.write_text(
        "\n".join(f"{a}\t{b}" for a, b in saved) + f"\n\ntotal={len(saved)}\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(saved)} PNG(s) to {OUT_DIR}")


if __name__ == "__main__":
    main()
