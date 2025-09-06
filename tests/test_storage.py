from pathlib import Path
import pandas as pd
from modules.storage import Storage, StorageConfig, Lead

def test_storage_roundtrip(tmp_path: Path):
    csv_path = tmp_path/"leads.csv"
    st = Storage(StorageConfig(csv_path=csv_path))
    ok, msg = st.append_lead(Lead(first_name="A", last_name="B", email="a@b.c", company="X", phone=""))
    assert ok
    df = st.load_df()
    assert not df.empty and set(["id","created_at","first_name"]).issubset(df.columns)

    # edit + overwrite
    df.loc[df.index[0], "company"] = "Y"
    ok, _ = st.overwrite_df(df)
    df2 = st.load_df()
    assert (df2.loc[df2.index[0], "company"] == "Y")
