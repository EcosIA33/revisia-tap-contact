# -*- coding: utf-8 -*-
from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple, List
from filelock import FileLock
import pandas as pd
from datetime import datetime

CSV_HEADERS = [
    "id", "created_at",
    "first_name", "last_name", "email", "phone",
    "company", "job", "interest", "utm_source", "ip_hash"
]

@dataclass
class StorageConfig:
    csv_path: Path

@dataclass
class Lead:
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    company: str = ""
    job: str = ""
    interest: str = ""
    utm_source: str = ""
    ip_hash: str = ""

class Storage:
    def __init__(self, cfg: StorageConfig):
        self.cfg = cfg
        self.cfg.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cfg.csv_path.exists():
            self._init_csv()

    def _init_csv(self) -> None:
        lock = FileLock(str(self.cfg.csv_path) + ".lock")
        with lock:
            with self.cfg.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)

    def load_df(self) -> pd.DataFrame:
        if not self.cfg.csv_path.exists():
            self._init_csv()
        df = pd.read_csv(self.cfg.csv_path, dtype=str)
        for col in CSV_HEADERS:
            if col not in df.columns:
                df[col] = ""
        df = df[CSV_HEADERS]
        return df.fillna("")

    def append_lead(self, lead: Lead) -> Tuple[bool, str]:
        """Append a lead as a new row."""
        lock = FileLock(str(self.cfg.csv_path) + ".lock")
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        row = {
            "id": datetime.utcnow().strftime("%Y%m%d%H%M%S%f"),
            "created_at": now,
            **asdict(lead),
        }
        with lock:
            file_exists = self.cfg.csv_path.exists()
            with self.cfg.csv_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                if not file_exists or self.cfg.csv_path.stat().st_size == 0:
                    writer.writeheader()
                writer.writerow(row)
        return True, "OK"

    def overwrite_df(self, df: "pd.DataFrame") -> Tuple[bool, str]:
        """Overwrite CSV with the provided dataframe (must contain CSV_HEADERS)."""
        lock = FileLock(str(self.cfg.csv_path) + ".lock")
        # Keep only expected columns and order
        safe_df = df.copy()
        for col in CSV_HEADERS:
            if col not in safe_df.columns:
                safe_df[col] = ""
        safe_df = safe_df[CSV_HEADERS].fillna("")
        with lock:
            safe_df.to_csv(self.cfg.csv_path, index=False, encoding="utf-8")
        return True, "OK"
