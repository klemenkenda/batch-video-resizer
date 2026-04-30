import os
from typing import List

from .estimator import _probe_json

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
PROCESSED_TAG_KEY = "video_resizer_processed"
PROCESSED_TAG_VALUE = "1"


def _has_processed_marker(path: str) -> bool:
    probe = _probe_json(path)
    if probe is None:
        return False

    tags = (probe.get("format") or {}).get("tags") or {}
    for key, value in tags.items():
        if key.lower() == PROCESSED_TAG_KEY and str(value).strip() == PROCESSED_TAG_VALUE:
            return True
    return False


def scan(directory: str, skip_marked: bool = True) -> List[str]:
    """Recursively find all video files under *directory*.

    Files whose stem already ends with ``_resized`` are excluded so that a
    second scan does not re-process previously generated outputs.
    When ``skip_marked`` is True, files with metadata marker
    ``video_resizer_processed=1`` are also excluded.
    """
    results: List[str] = []
    for root, _dirs, files in os.walk(directory):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            stem = os.path.splitext(name)[0]
            if stem.endswith("_resized"):
                continue
            full_path = os.path.abspath(os.path.join(root, name))
            if skip_marked and _has_processed_marker(full_path):
                continue
            results.append(full_path)
    return results
