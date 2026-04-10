from app.services.email_service import build_email_verification_html


def test_verification_email_contains_link():
    html = build_email_verification_html("alice", "https://example.com/confirm")
    assert "alice" in html
    assert "https://example.com/confirm" in html
