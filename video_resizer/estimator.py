import os
import shutil
import subprocess
from glob import glob
from dataclasses import dataclass
from typing import Tuple

import cv2
import ffmpeg


@dataclass
class VideoInfo:
    path: str
    orig_width: int
    orig_height: int
    new_width: int
    new_height: int
    orig_size_bytes: int
    est_size_bytes: int
    duration_seconds: float
    will_resize: bool  # False if already within target


def _even(n: int) -> int:
    """Round down to the nearest even integer (required by libx264)."""
    return (n // 2) * 2


def _compute_new_resolution(
    orig_w: int, orig_h: int, target_w: int, target_h: int
) -> Tuple[int, int, bool]:
    """Return (new_w, new_h, will_resize).

    Scales the video down to fit within target_w × target_h while maintaining
    aspect ratio.  If the video already fits, the original dimensions are
    returned unchanged.
    """
    if orig_w <= target_w and orig_h <= target_h:
        return orig_w, orig_h, False

    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = _even(int(orig_w * scale))
    new_h = _even(int(orig_h * scale))
    return new_w, new_h, True


def _resolve_ffprobe_cmd() -> str:
    """Return a working ffprobe command path, or plain 'ffprobe' as fallback."""
    candidates = []

    # Highest precedence: explicit user override.
    env_cmd = os.environ.get("FFPROBE_PATH")
    if env_cmd:
        candidates.append(env_cmd)

    path_cmd = shutil.which("ffprobe")
    if path_cmd:
        candidates.append(path_cmd)

    # Common winget install location on Windows.
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(
            local_app_data,
            "Microsoft",
            "WinGet",
            "Packages",
            "Gyan.FFmpeg_*",
            "ffmpeg-*",
            "bin",
            "ffprobe.exe",
        )
        matches = sorted(glob(pattern))
        if matches:
            candidates.extend(reversed(matches))

    candidates.append("ffprobe")

    for candidate in candidates:
        try:
            completed = subprocess.run(
                [candidate, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            if completed.returncode == 0:
                return candidate
        except (OSError, subprocess.SubprocessError):
            continue

    return "ffprobe"


def estimate(path: str, target_w: int = 1280, target_h: int = 720) -> VideoInfo:
    """Probe *path* with ffprobe and return a :class:`VideoInfo` estimate."""
    probe = None
    try:
        probe = ffmpeg.probe(path, cmd=_resolve_ffprobe_cmd())
    except ffmpeg.Error:
        # Fallback for environments where ffprobe binary is unavailable/broken.
        probe = None

    if probe is not None:
        # Locate the first video stream.
        video_stream = next(
            (s for s in probe["streams"] if s.get("codec_type") == "video"), None
        )
        if video_stream is None:
            raise RuntimeError(f"No video stream found in '{path}'")

        orig_w: int = int(video_stream["width"])
        orig_h: int = int(video_stream["height"])

        # Duration: prefer format-level value, fall back to stream.
        fmt = probe.get("format", {})
        try:
            duration = float(fmt.get("duration") or video_stream.get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0.0

        # Bitrate: prefer stream-level, fall back to container.
        try:
            bitrate = int(
                video_stream.get("bit_rate")
                or fmt.get("bit_rate")
                or 0
            )
        except (TypeError, ValueError):
            bitrate = 0
    else:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError(f"ffprobe failed and OpenCV could not open '{path}'")

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        cap.release()

        if orig_w <= 0 or orig_h <= 0:
            raise RuntimeError(f"Could not read video dimensions for '{path}'")

        duration = (frames / fps) if fps > 0 else 0.0
        bitrate = 0

    orig_size = os.path.getsize(path)

    # For portrait videos swap the target so the long side is still 1280.
    eff_target_w, eff_target_h = (target_h, target_w) if orig_h > orig_w else (target_w, target_h)
    new_w, new_h, will_resize = _compute_new_resolution(orig_w, orig_h, eff_target_w, eff_target_h)

    if not will_resize or bitrate == 0 or duration == 0:
        # Cannot estimate meaningfully; use original size as worst-case.
        est_size = orig_size
    else:
        pixel_ratio = (new_w * new_h) / (orig_w * orig_h)
        new_bitrate = bitrate * pixel_ratio
        # bytes = bits/s × seconds / 8, +10 % for audio & container overhead
        est_size = int(new_bitrate * duration / 8 * 1.10)

    return VideoInfo(
        path=path,
        orig_width=orig_w,
        orig_height=orig_h,
        new_width=new_w,
        new_height=new_h,
        orig_size_bytes=orig_size,
        est_size_bytes=est_size,
        duration_seconds=duration,
        will_resize=will_resize,
    )


def output_path(path: str) -> str:
    """Return the ``_resized.mp4`` sibling path for *path*."""
    stem = os.path.splitext(path)[0]
    return stem + "_resized.mp4"
