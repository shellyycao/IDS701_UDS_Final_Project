"""Extract PNG outputs from a Jupyter notebook into a figures directory.

Defaults follow the final-submission layout (extract from
`notebooks/dst_crime_ca_az_refined.ipynb` into `figures/memo_refined/`), but you can
override both paths via CLI args.
"""

from __future__ import annotations

import base64
import json
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = ROOT / "notebooks" / "dst_crime_ca_az_refined.ipynb"
DEFAULT_OUT_DIR = ROOT / "figures" / "memo_refined"


def slug(s: str, max_len: int = 50) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.ASCII)
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return (s[:max_len] or "figure").lower()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notebook",
        type=Path,
        default=DEFAULT_NOTEBOOK,
        help="Path to the input .ipynb notebook (default: notebooks/dst_crime_ca_az_refined.ipynb)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory to write extracted PNGs (default: figures/memo_refined)",
    )
    args = parser.parse_args()

    notebook_path: Path = args.notebook
    out_dir: Path = args.out_dir
    if not notebook_path.is_absolute():
        notebook_path = (ROOT / notebook_path).resolve()
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()

    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

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
            path = out_dir / fname
            path.write_bytes(raw)
            saved.append((fname, last_md_heading))

    manifest = out_dir / "MANIFEST.txt"
    manifest.write_text(
        "\n".join(f"{a}\t{b}" for a, b in saved) + f"\n\ntotal={len(saved)}\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(saved)} PNG(s) to {out_dir}")


if __name__ == "__main__":
    main()
