import io
from modules.qr import decode_qr_from_bytes, parse_contact_from_qr

def test_parse_mailto():
    parsed = parse_contact_from_qr("mailto:john.doe@example.com")
    assert parsed["email"] == "john.doe@example.com"

def test_parse_vcard_minimal():
    v = "BEGIN:VCARD\nVERSION:3.0\nN:Doe;John;;;\nEMAIL:john@example.com\nEND:VCARD\n"
    parsed = parse_contact_from_qr(v)
    assert parsed["first_name"] == "John"
    assert parsed["last_name"] == "Doe"
    assert parsed["email"] == "john@example.com"
