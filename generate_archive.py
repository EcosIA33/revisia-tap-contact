# -*- coding: utf-8 -*-
from __future__ import annotations
import shutil
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    zip_path = root / "revisia-tap-contact.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", root)
    print(f"Archive créée: {zip_path}")

if __name__ == "__main__":
    main()
