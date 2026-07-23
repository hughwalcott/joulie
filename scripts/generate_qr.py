"""One-shot dev script: regenerate assets/qrcodes/<tool_id>.png from the
tool registry. Not a runtime dependency — the PNGs are committed to the repo
so the kiosk works offline with no runtime QR generation.

Usage:
    source .venv/bin/activate
    pip install "qrcode[pil]>=7.4"
    python scripts/generate_qr.py
"""
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from joulie.tools import REGISTRY, qr_path

_QR_DIR = Path(__file__).parent.parent / "assets" / "qrcodes"


def main() -> None:
    _QR_DIR.mkdir(parents=True, exist_ok=True)
    for tool in REGISTRY.values():
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(tool.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#212529", back_color="#F8F9FA")
        img.save(qr_path(tool.id))
        print(f"  wrote {qr_path(tool.id).relative_to(Path.cwd())}  ({tool.url})")
    print(f"[qr] {len(REGISTRY)} codes written to {_QR_DIR}")


if __name__ == "__main__":
    main()
