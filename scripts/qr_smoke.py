
import sys, cv2, numpy as np
from modules.qr import decode_qr_from_bytes

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/qr_smoke.py <image_path>")
        sys.exit(1)
    path = sys.argv[1]
    with open(path, "rb") as f:
        b = f.read()
    res = decode_qr_from_bytes(b)
    print("Decoded:", res)
