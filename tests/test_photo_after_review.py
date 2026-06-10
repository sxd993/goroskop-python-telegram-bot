from pathlib import Path

from app.services import media


def test_find_photo_after_review_empty_dir(tmp_path: Path):
    assert media.find_photo_after_review(tmp_path) is None


def test_find_photo_after_review_missing_dir(tmp_path: Path):
    assert media.find_photo_after_review(tmp_path / "missing") is None


def test_find_photo_after_review_returns_image(tmp_path: Path):
    bonus = tmp_path / "bonus.png"
    bonus.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert media.find_photo_after_review(tmp_path) == bonus


def test_find_photo_after_review_ignores_non_images(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("not an image")
    bonus = tmp_path / "bonus.jpg"
    bonus.write_bytes(b"\xff\xd8\xff")
    assert media.find_photo_after_review(tmp_path) == bonus
