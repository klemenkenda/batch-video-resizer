import os
import re
import shutil
import subprocess
from glob import glob
from typing import Callable, Optional, Union

import ffmpeg

_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
_FPS_RE = re.compile(r"fps=\s*([\d.]+)")
_SPEED_RE = re.compile(r"speed=\s*([\d.]+x)")

from .estimator import VideoInfo, output_path, _resolve_ffprobe_cmd
from .logger import get_logger
from .scanner import PROCESSED_TAG_KEY, PROCESSED_TAG_VALUE


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _probe_media_summary(path: str) -> dict:
    """Return essential stream/duration info for consistency checks."""
    probe = ffmpeg.probe(path, cmd=_resolve_ffprobe_cmd())
    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    # Prefer format duration, fallback to first video stream duration.
    fmt_duration = _safe_float((probe.get("format") or {}).get("duration"), 0.0)
    vid_duration = _safe_float(video_streams[0].get("duration"), 0.0) if video_streams else 0.0
    duration = fmt_duration if fmt_duration > 0 else vid_duration

    return {
        "has_video": len(video_streams) > 0,
        "has_audio": len(audio_streams) > 0,
        "duration": duration,
    }


def _consistency_report(src_path: str, out_path: str) -> dict:
    """Return consistency report between source and output media."""
    src = _probe_media_summary(src_path)
    out = _probe_media_summary(out_path)
    issues = []

    if not out["has_video"]:
        issues.append("output has no video stream")

    if src["has_audio"] and not out["has_audio"]:
        issues.append("input has audio but output audio stream is missing")

    src_dur = src["duration"]
    out_dur = out["duration"]
    if src_dur > 0 and out_dur > 0:
        max_allowed_diff = max(1.0, src_dur * 0.02)
        if abs(src_dur - out_dur) > max_allowed_diff:
            issues.append(
                f"duration mismatch too large (input={src_dur:.2f}s, output={out_dur:.2f}s)"
            )

    return {
        "issues": issues,
        "src_has_audio": src["has_audio"],
        "out_has_audio": out["has_audio"],
        "src_duration": src["duration"],
        "out_duration": out["duration"],
    }


def _has_audio_stream(path: str) -> bool:
    """Return True if the input file contains at least one audio stream."""
    try:
        probe = ffmpeg.probe(path, cmd=_resolve_ffprobe_cmd())
    except ffmpeg.Error:
        # If probing fails, keep audio path enabled to avoid silent regressions.
        return True

    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "audio":
            return True
    return False


def _resolve_ffmpeg_cmd() -> str:
    """Return a working ffmpeg command path, or plain 'ffmpeg' as fallback."""
    candidates = []

    env_cmd = os.environ.get("FFMPEG_PATH")
    if env_cmd:
        candidates.append(env_cmd)

    path_cmd = shutil.which("ffmpeg")
    if path_cmd:
        candidates.append(path_cmd)

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
            "ffmpeg.exe",
        )
        matches = sorted(glob(pattern))
        if matches:
            candidates.extend(reversed(matches))

    candidates.append("ffmpeg")

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

    return "ffmpeg"


def process(
    info: VideoInfo,
    on_progress: Optional[Callable[[Union[str, dict]], None]] = None,
    crf: int = 26,
    codec: str = "h264",
) -> str:
    """Transcode the video described by *info* to an MP4 at ``_resized.mp4``.

    Parameters
    ----------
    info:
        A :class:`~video_resizer.estimator.VideoInfo` produced by
        :func:`~video_resizer.estimator.estimate`.
    on_progress:
        Optional callback invoked with a human-readable status string at key
        milestones (started, finished, skipped).

    Returns
    -------
    str
        Absolute path of the output file.

    Raises
    ------
    RuntimeError
        If FFmpeg exits with a non-zero code.
    """
    logger = get_logger()
    out = output_path(info.path)

    if os.path.exists(out):
        msg = f"Output already exists, skipping: {out}"
        logger.warning(msg)
        try:
            report = _consistency_report(info.path, out)
        except ffmpeg.Error as exc:
            raise RuntimeError(f"Consistency check failed for existing output '{out}': {exc}") from exc

        issues = report["issues"]
        if issues:
            issue_text = "; ".join(issues)
            raise RuntimeError(
                f"Consistency check failed for existing output '{out}': {issue_text}"
            )

        logger.info(
            "Consistency check passed (existing output): audio %s->%s, duration %.2fs->%.2fs",
            "yes" if report["src_has_audio"] else "no",
            "yes" if report["out_has_audio"] else "no",
            report["src_duration"],
            report["out_duration"],
        )
        if on_progress:
            on_progress({
                "status": "validated",
                "src_has_audio": report["src_has_audio"],
                "out_has_audio": report["out_has_audio"],
                "src_duration": report["src_duration"],
                "out_duration": report["out_duration"],
                "existing_output": True,
            })
            on_progress("skipped")
        return out

    if on_progress:
        on_progress("processing")

    logger.info("Processing: %s -> %s", info.path, out)
    logger.debug(
        "  Resolution: %dx%d -> %dx%d  (resize=%s)",
        info.orig_width,
        info.orig_height,
        info.new_width,
        info.new_height,
        info.will_resize,
    )

    input_stream = ffmpeg.input(info.path)
    video_stream = input_stream.video

    if info.will_resize:
        video_stream = video_stream.filter("scale", info.new_width, info.new_height)

    vcodec = "libx264" if codec == "h264" else "libx265"
    extra_opts = {"x265-params": "log-level=error"} if codec == "h265" else {}
    has_audio = _has_audio_stream(info.path)

    ffmpeg_cmd = _resolve_ffmpeg_cmd()
    output_kwargs = {
        "vcodec": vcodec,
        "crf": crf,
        "preset": "medium",
        "movflags": "+use_metadata_tags",
        "metadata:g": f"{PROCESSED_TAG_KEY}={PROCESSED_TAG_VALUE}",
        **extra_opts,
    }

    if has_audio:
        output_node = (
            ffmpeg
            .output(
                video_stream,
                input_stream.audio,
                out,
                acodec="aac",
                audio_bitrate="96k",
                **output_kwargs,
            )
            .overwrite_output()
        )
    else:
        output_node = (
            ffmpeg
            .output(
                video_stream,
                out,
                an=None,
                **output_kwargs,
            )
            .overwrite_output()
        )
    try:
        proc = output_node.run_async(pipe_stdout=True, pipe_stderr=True, cmd=ffmpeg_cmd)
    except OSError as exc:
        raise RuntimeError(f"FFmpeg could not start for '{info.path}': {exc}") from exc

    # ffmpeg writes progress lines ending with \r (not \n) on Windows,
    # so readline() would block until EOF. Read in chunks instead.
    stderr_lines = []
    _buf = b""
    while True:
        chunk = proc.stderr.read(512)
        if not chunk:
            break
        _buf += chunk
        parts = re.split(rb"[\r\n]", _buf)
        _buf = parts[-1]
        for raw_part in parts[:-1]:
            line = raw_part.decode(errors="replace").strip()
            if not line:
                continue
            stderr_lines.append(line)
            if on_progress and info.duration_seconds > 0:
                m_time = _TIME_RE.search(line)
                if m_time:
                    h = float(m_time.group(1))
                    mins = float(m_time.group(2))
                    secs = float(m_time.group(3))
                    elapsed = h * 3600 + mins * 60 + secs
                    pct = min(elapsed / info.duration_seconds, 1.0)
                    fps_m = _FPS_RE.search(line)
                    speed_m = _SPEED_RE.search(line)
                    on_progress({
                        "status": "progress",
                        "percent": pct,
                        "fps": fps_m.group(1) if fps_m else "",
                        "speed": speed_m.group(1) if speed_m else "",
                    })

    proc.wait()
    if proc.returncode != 0:
        stderr_tail = "".join(stderr_lines[-20:])
        raise RuntimeError(f"FFmpeg failed for '{info.path}':\n{stderr_tail}")

    try:
        report = _consistency_report(info.path, out)
    except ffmpeg.Error as exc:
        raise RuntimeError(f"Consistency check failed for '{out}': {exc}") from exc

    issues = report["issues"]
    if issues:
        issue_text = "; ".join(issues)
        raise RuntimeError(f"Consistency check failed for '{out}': {issue_text}")

    logger.info(
        "Consistency check passed: audio %s->%s, duration %.2fs->%.2fs",
        "yes" if report["src_has_audio"] else "no",
        "yes" if report["out_has_audio"] else "no",
        report["src_duration"],
        report["out_duration"],
    )
    if on_progress:
        on_progress({
            "status": "validated",
            "src_has_audio": report["src_has_audio"],
            "out_has_audio": report["out_has_audio"],
            "src_duration": report["src_duration"],
            "out_duration": report["out_duration"],
        })

    logger.info("Done: %s  (%s bytes)", out, os.path.getsize(out))
    if on_progress:
        on_progress("done")
    return out
