import argparse
import os
import shutil
import sys
import time

from .cleaner import cleanup, replace_originals
from .estimator import estimate, output_path
from .logger import get_logger
from .processor import process
from .scanner import scan


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _parse_resolution(value: str):
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"Resolution must be in WxH format, e.g. 1280x720, got: {value!r}"
        )


def _elide_right(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _table_widths(term_w: int):
    # Keep numeric columns readable, then give remaining space to file path.
    if term_w >= 100:
        size_w = 10
        res_w = 10
    elif term_w >= 84:
        size_w = 9
        res_w = 9
    else:
        size_w = 8
        res_w = 8

    separators = 8  # four "  " separators
    file_w = max(16, term_w - (size_w + res_w + res_w + size_w + separators))
    return file_w, size_w, res_w


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video_resizer",
        description="Batch resize videos to a target resolution and convert to MP4.",
    )
    parser.add_argument("input_dir", help="Directory containing videos to process.")
    parser.add_argument(
        "--resolution",
        metavar="WxH",
        type=_parse_resolution,
        default=(1280, 720),
        help="Target resolution (default: 1280x720). Videos smaller than this are not upscaled.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate sizes and print a report without processing any files.",
    )
    post_group = parser.add_mutually_exclusive_group()
    post_group.add_argument(
        "--cleanup",
        action="store_true",
        help="After processing, delete originals whose _resized.mp4 is healthy.",
    )
    post_group.add_argument(
        "--replace-originals",
        action="store_true",
        help="After successful processing, delete originals and rename healthy _resized.mp4 files to original names.",
    )
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        default="video_resizer.log",
        help="Path for the log file (default: video_resizer.log in CWD).",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=26,
        metavar="N",
        help="Constant Rate Factor controlling quality/size trade-off (default: 26). "
             "Lower = better quality, larger file. Typical range: 18-30.",
    )
    parser.add_argument(
        "--codec",
        choices=["h264", "h265"],
        default="h264",
        help="Video codec: h264 (default, fast, compatible) or h265 (50%% smaller, slower).",
    )
    parser.add_argument(
        "--include-processed",
        action="store_true",
        help="Include files already marked as processed in metadata (default: skip them).",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Console logging only for dry-run; during real processing the progress bar owns stdout.
    logger = get_logger(args.log_file, console=args.dry_run)

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        logger.error("Not a directory: %s", input_dir)
        return 2

    target_w, target_h = args.resolution

    logger.info("Scanning: %s", input_dir)
    paths = scan(input_dir, skip_marked=not args.include_processed)
    if not paths:
        logger.info("No video files found.")
        return 0

    logger.info("Found %d video file(s).", len(paths))

    # --- Estimation / dry-run table ---
    infos = []
    estimation_errors = []
    for path in paths:
        try:
            infos.append(estimate(path, target_w, target_h))
        except RuntimeError as exc:
            logger.error("Estimation failed: %s", exc)
            estimation_errors.append(path)

    term_w = shutil.get_terminal_size((120, 24)).columns
    col_w, size_w, res_w = _table_widths(term_w)

    # ANSI colors for the estimation table.
    _R = "\033[0m"
    _TH = "\033[1;36m"  # header
    _TF = "\033[33m"    # file
    _TN = "\033[32m"    # numeric/size
    _TR = "\033[36m"    # resolutions
    _TS = "\033[2m"     # separator

    row_fmt = (
        f"{{file:<{col_w}}}  "
        f"{{orig:>{size_w}}}  "
        f"{{orig_res:>{res_w}}}  "
        f"{{new_res:>{res_w}}}  "
        f"{{est:>{size_w}}}"
    )
    header = row_fmt.format(
        file="File",
        orig="Orig",
        orig_res="OrigRes",
        new_res="NewRes",
        est="EstSize",
    )
    sep_len = len(header)
    print(f"{_TH}{header}{_R}")
    print(f"{_TS}{'-' * sep_len}{_R}")

    total_orig = 0
    total_est = 0
    for info in infos:
        rel = os.path.relpath(info.path, input_dir)
        rel_display = _elide_right(rel, col_w)
        orig_res = f"{info.orig_width}x{info.orig_height}"
        new_res = f"{info.new_width}x{info.new_height}"
        print(
            f"{_TF}{rel_display:<{col_w}}{_R}  "
            f"{_TN}{_fmt_bytes(info.orig_size_bytes):>{size_w}}{_R}  "
            f"{_TR}{orig_res:>{res_w}}{_R}  "
            f"{_TR}{new_res:>{res_w}}{_R}  "
            f"{_TN}{_fmt_bytes(info.est_size_bytes):>{size_w}}{_R}"
        )
        total_orig += info.orig_size_bytes
        total_est += info.est_size_bytes

    print(f"{_TS}{'-' * sep_len}{_R}")
    print(
        f"{_TH}{'TOTAL':<{col_w}}{_R}  "
        f"{_TN}{_fmt_bytes(total_orig):>{size_w}}{_R}  "
        f"{_TS}{'-':>{res_w}}{_R}  "
        f"{_TS}{'-':>{res_w}}{_R}  "
        f"{_TN}{_fmt_bytes(total_est):>{size_w}}{_R}"
    )

    if args.dry_run:
        if args.cleanup:
            print("\n[dry-run] Cleanup: checking which originals would be deleted...")
            cleanup(paths, dry_run=True)
        if args.replace_originals:
            print("\n[dry-run] Replace originals: checking which files would be replaced...")
            replace_originals(paths, dry_run=True)
        return 0

    # --- Real processing ---
    BAR_WIDTH = 20
    FNAME_W = 20
    total_files = len(infos)

    # ANSI color helpers
    _R  = "\033[0m"
    _FOLDER  = "\033[1;36m"   # bold cyan  — folder
    _FNAME   = "\033[33m"     # yellow     — filename
    _IDX     = "\033[36m"     # cyan       — [N/M]
    _FILL    = "\033[32m"     # green      — filled bar
    _EMPTY   = "\033[2m"      # dim        — empty bar
    _PCT     = "\033[1m"      # bold       — percentage
    _EXTRA   = "\033[2m"      # dim        — fps / speed
    _ARROW   = "\033[1;32m"   # bold green — completion arrow
    _ERR     = "\033[1;31m"   # bold red   — errors
    _OK      = "\033[32m"     # green      — validation ok
    _SKIP    = "\033[33m"     # yellow     — skipped

    def _split_path(rel: str):
        parts = rel.replace("\\", "/").split("/")
        if len(parts) >= 2:
            return "/".join(parts[:-1]), parts[-1]
        return "", rel

    def _render_bar(file_idx: int, filename: str, pct: float, fps: str, speed: str) -> None:
        import shutil as _shutil
        term_w = _shutil.get_terminal_size((80, 24)).columns - 1
        filled = int(BAR_WIDTH * pct)
        display = filename if len(filename) <= FNAME_W else "..." + filename[-(FNAME_W - 3):]
        pct_str = f"{pct * 100:5.1f}%"

        # Measure base visible length (no ANSI), then add extras only if they fit.
        base_vis = len(f"[{file_idx}/{total_files}] {display:<{FNAME_W}}  [{'':{'<'}{BAR_WIDTH}}] {pct_str}")
        extras_vis = ""
        if fps:
            cand = f"  fps={fps}"
            if base_vis + len(extras_vis) + len(cand) <= term_w:
                extras_vis += cand
        if speed:
            cand = f"  speed={speed}"
            if base_vis + len(extras_vis) + len(cand) <= term_w:
                extras_vis += cand

        visible_len = base_vis + len(extras_vis)
        padding = " " * max(0, term_w - visible_len)

        colored = (
            f"{_IDX}[{file_idx}/{total_files}]{_R} "
            f"{_FNAME}{display:<{FNAME_W}}{_R}  "
            f"[{_FILL}{'█' * filled}{_R}"
            f"{_EMPTY}{'░' * (BAR_WIDTH - filled)}{_R}] "
            f"{_PCT}{pct_str}{_R}"
            f"{_EXTRA}{extras_vis}{_R}"
        )
        sys.stdout.write("\r" + colored + padding)
        sys.stdout.flush()

    errors = list(estimation_errors)
    processed = []
    last_folder = None
    for file_idx, info in enumerate(infos, start=1):
        rel = os.path.relpath(info.path, input_dir)
        folder, filename = _split_path(rel)
        out_file = os.path.basename(output_path(info.path))
        start_time = time.monotonic()

        if folder != last_folder:
            sys.stdout.write(f"\n{_FOLDER}{folder}/{_R}\n")
            sys.stdout.flush()
            last_folder = folder
        _render_bar(file_idx, filename, 0.0, "", "")
        validation_note = ""
        skipped = False

        def _on_progress(event, _idx=file_idx, _fname=filename):
            nonlocal validation_note, skipped
            if isinstance(event, dict) and event.get("status") == "progress":
                _render_bar(_idx, _fname, event["percent"], event["fps"], event["speed"])
            elif isinstance(event, dict) and event.get("status") == "validated":
                src_a = "yes" if event.get("src_has_audio") else "no"
                out_a = "yes" if event.get("out_has_audio") else "no"
                src_d = float(event.get("src_duration") or 0.0)
                out_d = float(event.get("out_duration") or 0.0)
                delta = abs(src_d - out_d)
                basis = "existing" if event.get("existing_output") else "new"
                validation_note = (
                    f"  {_OK}check: ok ({basis}) audio {src_a}->{out_a} dur Δ{delta:.2f}s{_R}"
                )
            elif event == "skipped":
                skipped = True

        try:
            process(info, on_progress=_on_progress, crf=args.crf, codec=args.codec)
            elapsed = time.monotonic() - start_time
            out_size = os.path.getsize(output_path(info.path))
            reduction = (1.0 - out_size / info.orig_size_bytes) * 100 if info.orig_size_bytes else 0
            display = filename if len(filename) <= FNAME_W else "..." + filename[-(FNAME_W - 3):]
            if skipped:
                done_line = (
                    f"{_IDX}[{file_idx}/{total_files}]{_R} "
                    f"{_FNAME}{display:<{FNAME_W}}{_R}  "
                    f"[{_SKIP}{'=' * BAR_WIDTH}{_R}] "
                    f"{_SKIP}SKIPPED{_R}  "
                    f"{_ARROW}-> {out_file}{_R}  "
                    f"{_fmt_bytes(out_size)} ({reduction:+.1f}%)"
                    f"{validation_note}"
                )
            else:
                done_line = (
                    f"{_IDX}[{file_idx}/{total_files}]{_R} "
                    f"{_FNAME}{display:<{FNAME_W}}{_R}  "
                    f"[{_FILL}{'█' * BAR_WIDTH}{_R}] "
                    f"{_PCT}100.0%{_R}  "
                    f"{_ARROW}-> {out_file}{_R}  "
                    f"{_fmt_bytes(out_size)} ({reduction:+.1f}%)  {elapsed:.0f}s"
                    f"{validation_note}"
                )
            sys.stdout.write("\r" + done_line + "\n")
            sys.stdout.flush()
            processed.append(info.path)
        except RuntimeError as exc:
            sys.stdout.write("\n")
            sys.stdout.write(f"{_ERR}ERROR{_R} {filename}: {exc}\n")
            sys.stdout.flush()
            logger.error("Processing failed: %s", exc)
            errors.append(info.path)

    logger.info(
        "Processing complete. Success: %d  Errors: %d",
        len(processed),
        len(errors),
    )
    if errors:
        sys.stdout.write(f"{_ERR}Completed with {len(errors)} error(s). See log for details.{_R}\n")
        sys.stdout.flush()

    # --- Cleanup ---
    if args.cleanup and processed:
        logger.info("Running cleanup on %d processed file(s)...", len(processed))
        result = cleanup(processed)
        logger.info(
            "Cleanup: deleted=%d  skipped=%d  failed=%d",
            len(result.deleted),
            len(result.skipped),
            len(result.failed),
        )
        errors.extend(result.failed)

    # --- Replace Originals (Second Pass) ---
    if args.replace_originals and processed:
        if errors:
            logger.warning(
                "Skipping replace-originals pass because processing had %d error(s).",
                len(errors),
            )
            sys.stdout.write(
                f"{_ERR}Skipping replace-originals pass due to earlier errors.{_R}\n"
            )
            sys.stdout.flush()
        else:
            logger.info("Running replace-originals pass on %d file(s)...", len(processed))
            result = replace_originals(processed)
            logger.info(
                "Replace-originals: replaced=%d  skipped=%d  failed=%d",
                len(result.replaced),
                len(result.skipped),
                len(result.failed),
            )
            sys.stdout.write(
                f"{_OK}Second pass complete: replaced={len(result.replaced)} "
                f"skipped={len(result.skipped)} failed={len(result.failed)}{_R}\n"
            )
            sys.stdout.flush()
            errors.extend(result.failed)

    if errors:
        return 1
    return 0
