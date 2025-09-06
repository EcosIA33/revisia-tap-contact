# -*- coding: utf-8 -*-
from __future__ import annotations
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from filelock import FileLock

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except Exception:  # pragma: no cover
    gspread = None
    ServiceAccountCredentials = None  # type: ignore

@dataclass
class Lead:
    first_name: str
    last_name: str
    email: str
    phone: str
    company: str
    job: str
    interest: str
    utm_source: str
    ip_hash: str

@dataclass
class StorageConfig:
    csv_path: Path
    gsheet_id: Optional[str] = None
    gservice_json: Optional[str] = None

class Storage:
    def __init__(self, cfg: StorageConfig) -> None:
        self.cfg = cfg
        self.cfg.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.cfg.csv_path.exists():
            with open(self.cfg.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "first_name","last_name","email","phone","company",
                    "job","interest","utm_source","ip_hash"
                ])

    def save_lead(self, lead: Lead) -> Tuple[bool, str]:
        try:
            lock = FileLock(str(self.cfg.csv_path) + ".lock")
            with lock:
                with open(self.cfg.csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        lead.first_name, lead.last_name, lead.email, lead.phone,
                        lead.company, lead.job, lead.interest, lead.utm_source, lead.ip_hash
                    ])
        except Exception as e:
            return False, f"CSV error: {e}"

        if self.cfg.gsheet_id and self.cfg.gservice_json and gspread and ServiceAccountCredentials:
            try:
                scope = ["https://spreadsheets.google.com/feeds",
                         "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_name(self.cfg.gservice_json, scope)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(self.cfg.gsheet_id).sheet1
                sheet.append_row([
                    lead.first_name, lead.last_name, lead.email, lead.phone,
                    lead.company, lead.job, lead.interest, lead.utm_source, lead.ip_hash
                ])
            except Exception as e:
                return True, f"Lead enregistré (CSV). Google Sheets: {e}"
        return True, "OK"
