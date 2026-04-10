from pathlib import Path


def test_readme_mentions_fastapi():
    readme = Path("README.md").read_text()
    assert "FastAPI" in readme
    assert "Neon" in readme
