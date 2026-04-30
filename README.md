# Video Resizer Studio

Batch video conversion tool with:
- GUI and CLI modes
- Resolution-aware resizing (including portrait handling)
- Real-time progress reporting
- Audio-preserving transcode pipeline
- Post-conversion consistency checks
- Optional second pass to replace originals
- Metadata marking to detect already processed files

The tool is especially useful for resizing large video collections to fit within specific resolution bounds (e.g. 720p) while preserving quality and aspect ratio, where video quality is less important than file size and compatibility. Examples include resizing smartphone videos for easier sharing or archiving (such as west coast swing classes and comps videos).

Runtime dependencies include FFmpeg tooling plus Python package `opencv-python` (cv2), which is bundled into the Windows EXE/installer builds.

## Windows v1.0.2 Download

- Release page: https://github.com/klemenkenda/batch-video-resizer/releases/tag/v1.0.2
- Windows installer (.exe): https://github.com/klemenkenda/batch-video-resizer/releases/download/v1.0.2/VideoResizerStudio-Setup-v1.0.2.exe
- Portable build (.zip): https://github.com/klemenkenda/batch-video-resizer/releases/download/v1.0.2/VideoResizerStudio-v1.0.2-win64.zip

## What This Project Does

This project scans a folder recursively (including all subdirectories), finds video files, and converts them to MP4 using FFmpeg.

Key behaviors:
- Keeps aspect ratio
- Avoids upscaling when source already fits target bounds
- Uses even dimensions required by H.264/H.265 encoders
- Preserves audio when present
- Validates output stream consistency after conversion

## Quick Manual

### Recursive scan behavior
- The selected input folder is scanned recursively.
- All supported video files in subdirectories are included.

### Processed-file detection (metadata)
- Converted outputs are tagged with metadata marker: `video_resizer_processed=1`
- Files with this marker are skipped by default to prevent accidental re-processing.
- Override when needed:
  - CLI: use `--include-processed`
  - GUI: enable "Include already processed"

### Delete originals vs replace originals
- Delete originals after processing:
  - Keeps resized outputs as separate files.
  - Removes original files after health validation.

- Second pass: replace originals with resized:
  - Validates resized outputs.
  - Deletes original files.
  - Renames resized files back to the original filenames.
  - Best option when you want final files to keep original names.

## Running the App

### GUI mode
```powershell
python main.py
```

### CLI mode
```powershell
python main.py --no-gui <input_dir> [options]
python main.py --no-gui --help
```

## Important CLI Options

- `--resolution WxH`: target bounding box (default: 1280x720)
- `--dry-run`: estimate only, no conversion
- `--cleanup`: delete originals after successful validation
- `--replace-originals`: delete original and rename resized to original name
- `--include-processed`: include metadata-marked files (normally skipped)
- `--crf N`: quality/size tradeoff (default: 26)
- `--codec {h264,h265}`
- `--log-file PATH`

## Build EXE and Installer (Windows)

### EXE
```powershell
python -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```
Output:
- `dist\\VideoResizerStudio\\VideoResizerStudio.exe`

### Installer
Requirements:
- Inno Setup 6 installed

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 -AppVersion 1.0.0
```
Output:
- `dist\\installer\\VideoResizerStudio-Setup-1.0.0.exe`

## Release Automation

Workflow:
- `.github/workflows/release.yml`

On tag push (`v*`), GitHub Actions builds and publishes:
- Installer EXE
- Portable ZIP

## Troubleshooting

- If README is not rendered on GitHub, ensure file encoding is UTF-8 text.
- If cleanup/replace fails with access denied, close Explorer preview/media players and retry.

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE).
