import os
import stat
import time
from dataclasses import dataclass, field
from typing import List

import ffmpeg

from .estimator import output_path, _resolve_ffprobe_cmd
from .logger import get_logger


@dataclass
class CleanupResult:
    deleted: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)


@dataclass
class ReplaceResult:
    replaced: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)


def _is_healthy(resized_path: str) -> bool:
    """Return True only if *resized_path* exists, is non-empty, and ffprobe
    can parse a valid video stream from it."""
    if not os.path.isfile(resized_path):
        return False
    if os.path.getsize(resized_path) == 0:
        return False
    try:
        probe = ffmpeg.probe(resized_path, cmd=_resolve_ffprobe_cmd())
    except ffmpeg.Error:
        return False
    return any(
        s.get("codec_type") == "video" for s in probe.get("streams", [])
    )


def _delete_file(path: str, logger) -> bool:
    """Delete a file with Windows-friendly retries and permission fixes."""
    if not os.path.exists(path):
        return True

    for attempt in range(2):
        try:
            os.remove(path)
            return True
        except PermissionError as exc:
            # Common on Windows when file is read-only or briefly locked.
            try:
                os.chmod(path, stat.S_IWRITE)
            except OSError:
                pass

            if attempt == 0:
                time.sleep(0.2)
                continue

            if getattr(exc, "winerror", None) == 5:
                logger.error(
                    "Access denied deleting '%s'. File may be in use by another app (e.g. player/explorer preview).",
                    path,
                )
            else:
                logger.error("Failed to delete '%s': %s", path, exc)
        except OSError as exc:
            logger.error("Failed to delete '%s': %s", path, exc)

    return False


def cleanup(original_paths: List[str], dry_run: bool = False) -> CleanupResult:
    """Delete originals whose ``_resized.mp4`` sibling is healthy.

    Parameters
    ----------
    original_paths:
        Absolute paths to the *original* (non-resized) video files.
    dry_run:
        When True, report what would be deleted without touching any files.

    Returns
    -------
    CleanupResult
        Lists of deleted, skipped (no healthy resized sibling), and failed
        (validation check failed) original paths.
    """
    logger = get_logger()
    result = CleanupResult()

    for orig in original_paths:
        resized = output_path(orig)

        if not os.path.exists(resized):
            logger.debug("No resized sibling found, skipping cleanup: %s", orig)
            result.skipped.append(orig)
            continue

        if not _is_healthy(resized):
            logger.warning(
                "Resized file failed health check, keeping original: %s", resized
            )
            result.failed.append(orig)
            continue

        if dry_run:
            logger.info("[dry-run] Would delete original: %s", orig)
            result.deleted.append(orig)
        else:
            if _delete_file(orig, logger):
                logger.info("Deleted original: %s", orig)
                result.deleted.append(orig)
            else:
                result.failed.append(orig)

    return result


def replace_originals(original_paths: List[str], dry_run: bool = False) -> ReplaceResult:
    """Replace originals with validated ``_resized.mp4`` siblings.

    For each original path:
    1) validate ``*_resized.mp4`` health,
    2) delete original if it exists,
    3) rename ``*_resized.mp4`` to original path.
    """
    logger = get_logger()
    result = ReplaceResult()

    for orig in original_paths:
        resized = output_path(orig)

        if not os.path.exists(resized):
            logger.debug("No resized sibling found, skipping replace: %s", orig)
            result.skipped.append(orig)
            continue

        if not _is_healthy(resized):
            logger.warning("Resized file failed health check, cannot replace original: %s", resized)
            result.failed.append(orig)
            continue

        if dry_run:
            if os.path.exists(orig):
                logger.info("[dry-run] Would delete original: %s", orig)
            logger.info("[dry-run] Would rename '%s' -> '%s'", resized, orig)
            result.replaced.append(orig)
            continue

        try:
            if os.path.exists(orig):
                if not _delete_file(orig, logger):
                    result.failed.append(orig)
                    continue
                logger.info("Deleted original: %s", orig)

            os.replace(resized, orig)
            logger.info("Renamed resized to original name: %s -> %s", resized, orig)
            result.replaced.append(orig)
        except OSError as exc:
            logger.error("Failed to replace '%s' with '%s': %s", orig, resized, exc)
            result.failed.append(orig)

    return result
