
"""
Persistent storage for leads using SQLite (stdlib only).

- Default DB file: data/leads.db (override with env LEADS_DB_PATH)
- Safe import multiple times.
- API: init_db(path=None), upsert_lead(...), list_leads(), delete_lead(id), export_csv_bytes()
"""

from __future__ import annotations
import os, sqlite3, datetime, csv, io, threading

DB_PATH = os.getenv("LEADS_DB_PATH", "data/leads.db")
_CONN = None
_LOCK = threading.RLock()


def _connect(db_path: str) -> sqlite3.Connection:
    folder = os.path.dirname(db_path) or "."
    os.makedirs(folder, exist_ok=True)
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name  TEXT,
        email      TEXT UNIQUE,
        phone      TEXT,
        company    TEXT,
        job        TEXT,
        source     TEXT,
        consent    INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)")
    return con


def init_db(path: str | None = None) -> str:
    """Initialize (or reuse) the SQLite DB. Returns DB path."""
    global DB_PATH, _CONN
    with _LOCK:
        if path:
            DB_PATH = path
        if _CONN is None:
            _CONN = _connect(DB_PATH)
        return DB_PATH


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def upsert_lead(first_name: str, last_name: str, email: str, phone: str,
                company: str, job: str, source: str, consent: bool) -> None:
    """Insert or update a lead by unique email (idempotent writes)."""
    if not email:
        raise ValueError("email is required for persistence (unique key)")
    now = _now_iso()
    with _LOCK, _CONN:
        _CONN.execute(
            """
            INSERT INTO leads (first_name,last_name,email,phone,company,job,source,consent,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(email) DO UPDATE SET
              first_name=excluded.first_name,
              last_name=excluded.last_name,
              phone=excluded.phone,
              company=excluded.company,
              job=excluded.job,
              source=excluded.source,
              consent=excluded.consent,
              updated_at=excluded.updated_at
            """,
            (first_name or "", last_name or "", (email or "").strip().lower(), phone or "",
             company or "", job or "", source or "", int(bool(consent)), now, now)
        )


def list_leads(order: str = "updated_at DESC") -> list[dict]:
    with _LOCK:
        cur = _CONN.execute(f"SELECT id, first_name,last_name,email,phone,company,job,source,consent,created_at,updated_at FROM leads ORDER BY {order}")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def delete_lead(lead_id: int) -> None:
    with _LOCK, _CONN:
        _CONN.execute("DELETE FROM leads WHERE id=?", (int(lead_id),))


def export_csv_bytes() -> bytes:
    """Return CSV export as bytes (for Streamlit download_button)."""
    rows = list_leads()
    headers = ["id","first_name","last_name","email","phone","company","job","source","consent","created_at","updated_at"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=headers)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in headers})
    return buf.getvalue().encode("utf-8")
