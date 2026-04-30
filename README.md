# Video Resizer Studio

Batch video conversion tool with:
- GUI and CLI modes
- Resolution-aware resizing (including portrait handling)
- Real-time progress reporting
- Audio-preserving transcode pipeline
- Post-conversion consistency checks
- Optional second pass to replace originals
- Metadata marking to detect already processed files

## What This Project Does

This project scans a folder recursively, finds video files, and converts them to MP4 using FFmpeg.

Key behaviors:
- Keeps aspect ratio
- Avoids upscaling when source already fits target bounds
- Uses even dimensions required by H.264/H.265 encoders
- Preserves audio when present
- Validates output stream consistency after conversion
- Supports cleanup workflows:
  - Delete originals after successful output validation
  - Replace originals with validated outputs

## Project Structure

- main.py: Entry point, starts GUI or CLI
- requirements.txt: Python dependencies
- video_resizer/cli.py: CLI workflow and terminal UI
- video_resizer/gui.py: PyQt GUI workflow
- video_resizer/scanner.py: File discovery and processed-marker filtering
- video_resizer/estimator.py: Probe and estimation logic
- video_resizer/processor.py: FFmpeg transcode and consistency checks
- video_resizer/cleaner.py: Cleanup and replace-originals passes
- video_resizer/logger.py: File/console logging setup

## Requirements

- Windows (primary tested platform)
- Python 3.10+
- FFmpeg + FFprobe available

Python packages:
- ffmpeg-python>=0.2.0
- PyQt6==6.7.1

Install:

```powershell
pip install -r requirements.txt
```

## FFmpeg and FFprobe

The app resolves FFmpeg/FFprobe in this order:
1. Environment override path
2. PATH lookup
3. Common WinGet install location
4. Fallback command name

Optional environment overrides:
- FFMPEG_PATH
- FFPROBE_PATH

If your system PATH is inconsistent, set these explicitly.

## Running the App

### GUI Mode

```powershell
python main.py
```

GUI highlights:
- Modern light theme
- Full-screen support:
  - Button: Full Screen
  - Shortcut: F11 toggle
  - Shortcut: Esc exits full-screen
- Per-file graphical progress bars in Status column
- Colored and readable log panel by level
- Actual output size shown after each file finishes
- Optional include-processed toggle during scan

### CLI Mode

General:

```powershell
python main.py --no-gui <input_dir> [options]
```

Help:

```powershell
python main.py --no-gui --help
```

## Quick Manual

### Recursive Scan Behavior

- The selected input folder is scanned recursively.
- All supported video files in subdirectories are included.

### Processed-File Detection (Metadata)

- Converted outputs are tagged with metadata marker:
  - video_resizer_processed=1
- Files with this marker are skipped by default to prevent accidental re-processing.
- Override when needed:
  - CLI: use --include-processed
  - GUI: enable Include already processed

### Delete Originals vs Replace Originals

- Delete originals after processing:
  - Keeps resized outputs as separate files.
  - Removes original files after health validation.

- Second pass: replace originals with resized:
  - Validates resized outputs.
  - Deletes original files.
  - Renames resized files back to the original filenames.
  - Best option when you want final files to keep original names.

## CLI Options

- input_dir
  - Required. Root directory to scan recursively.

- --resolution WxH
  - Target bounding box, default: 1280x720.
  - No upscaling if source already fits.
  - Portrait sources are handled by orientation-aware bounds.

- --dry-run
  - Probe + estimate only, no processing.

- --cleanup
  - After processing, delete originals when validated resized sibling is healthy.

- --replace-originals
  - Second pass: delete original then rename validated resized file to original name.
  - Mutually exclusive with --cleanup.

- --include-processed
  - Include files marked as already processed in metadata.
  - By default, marked files are skipped.

- --crf N
  - Constant Rate Factor for quality/size tradeoff, default: 26.

- --codec {h264,h265}
  - Video codec choice.

- --log-file PATH
  - Log path, default: video_resizer.log in current directory.

## Processing and Validation Pipeline

For each file:
1. Probe source media
2. Compute output dimensions
3. Encode with FFmpeg
4. Run post-conversion consistency checks

Consistency checks include:
- Output has a video stream
- If input had audio, output must have audio
- Duration delta stays within tolerance

If check fails:
- File is marked as error
- Error is shown (red in CLI)
- Error is logged

If output already exists:
- Existing output is validated
- File is marked as skipped (validated)

## Metadata Marker for Processed Files

To support renamed outputs (where _resized is removed), converted outputs are tagged with metadata:

- video_resizer_processed=1

Scanner behavior:
- Default: skips files with this marker
- Override: --include-processed (CLI) or Include already processed (GUI)

This allows re-run safety even after second-pass rename workflows.

## Second Pass Workflows

### Cleanup

- Keeps resized files as separate outputs
- Deletes original files after healthy-output validation

### Replace Originals

- Validates resized outputs
- Deletes original files
- Renames resized files to original names
- Includes Windows-safe deletion handling (read-only removal + retry)

## Logging

CLI:
- Dry-run: console + file logging
- Real processing: progress-driven terminal output, log file records details

GUI:
- Rich colored logs by level in log pane
- Log file still records all events

## Common Troubleshooting

### FFprobe/FFmpeg not found or failing

- Install FFmpeg/FFprobe
- Set FFMPEG_PATH and FFPROBE_PATH explicitly if needed
- Verify binaries run manually:

```powershell
ffmpeg -version
ffprobe -version
```

### Audio missing in output

- Current pipeline explicitly maps audio when present
- Consistency checks now fail conversion if input audio disappears

### Access denied on cleanup/replace

- Close file explorers/players using the file
- Ensure cloud sync tools are not locking files
- Retry operation (cleanup has Windows retry handling)

### GUI does not show newest changes

- Close all old app windows
- Relaunch from updated project folder

## Development Notes

Run from project root:

```powershell
python main.py
python main.py --no-gui videos --dry-run
```

Suggested test matrix:
- Landscape sources
- Portrait sources
- With and without audio
- Existing outputs present
- Replace-originals flow

## Versioning

Current intended release target: 1.0.0

When preparing release artifacts (EXE + installer), keep this README as source-of-truth behavior documentation.

## Build EXE and Installer

### Local EXE build (Windows)

From project root:

```powershell
python -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Output:
- dist\VideoResizerStudio\VideoResizerStudio.exe

### Local installer build (Windows)

Requirements:
- Inno Setup 6 installed (ISCC.exe available)

Build command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 -AppVersion 1.0.0
```

Output:
- dist\installer\VideoResizerStudio-Setup-1.0.0.exe

## GitHub Release Automation (v1.0.0)

Workflow file:
- .github/workflows/release.yml

Behavior:
- Trigger: push tag matching v*
- Builds portable EXE (zip) and installer on windows-latest
- Publishes both artifacts to GitHub Release

Expected release artifacts:
- VideoResizerStudio-v1.0.0-win64.zip
- VideoResizerStudio-Setup-v1.0.0.exe

### First-time Git setup (if needed)

If this folder is not yet a git repository:

```powershell
git init
git add .
git commit -m "Release prep v1.0.0"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

Create and push release tag:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

After tag push, GitHub Actions will build and publish the release automatically.

## License

Add your preferred license file before public release.
#   b a t c h - v i d e o - r e s i z e r 
 
 