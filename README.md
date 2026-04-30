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

This project scans a folder recursively (including all subdirectories), finds video files, and converts them to MP4 using FFmpeg.

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
- requirements-dev.txt: Build/release dependencies
- video_resizer/cli.py: CLI workflow and terminal UI
- video_resizer/gui.py: PyQt GUI workflow
- video_resizer/scanner.py: File discovery and processed-marker filtering
- video_resizer/estimator.py: Probe and estimation logic
- video_resizer/processor.py: FFmpeg transcode and consistency checks
- video_resizer/cleaner.py: Cleanup and replace-originals passes
- video_resizer/logger.py: File/console logging setup
- scripts/: Build and helper scripts
- installer/: Inno Setup installer script

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
- Quick Manual button with usage guidance
- Optional Include already processed toggle during scan

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

## Logging

CLI:
- Dry-run: console + file logging
- Real processing: progress-driven terminal output, log file records details

GUI:
- Rich colored logs by level in log pane
- Log file still records all events

## Build EXE and Installer

### Local EXE build (Windows)

```powershell
python -m pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Output:
- dist\VideoResizerStudio\VideoResizerStudio.exe

### Local installer build (Windows)

Requirements:
- Inno Setup 6 installed (ISCC.exe available)

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
- VideoResizerStudio-Setup-1.0.0.exe

## Troubleshooting

### FFprobe/FFmpeg not found or failing

- Install FFmpeg/FFprobe
- Set FFMPEG_PATH and FFPROBE_PATH explicitly if needed
- Verify binaries run manually

### Access denied on cleanup/replace

- Close file explorers/players using the file
- Ensure cloud sync tools are not locking files
- Retry operation (Windows-safe delete logic handles read-only + retry)

### README not rendered on GitHub

- Ensure file is UTF-8 text (no UTF-16/null-byte corruption)

## Versioning

Current intended release target: 1.0.0

## License

Add your preferred license file before public release.
믯⎿嘠摩潥删獥穩牥匠畴楤൯ഊ䈊瑡档瘠摩潥挠湯敶獲潩⁮潴汯眠瑩㩨਍‭啇⁉湡⁤䱃⁉潭敤൳ⴊ删獥汯瑵潩⵮睡牡⁥敲楳楺杮⠠湩汣摵湩⁧潰瑲慲瑩栠湡汤湩⥧਍‭敒污琭浩⁥牰杯敲獳爠灥牯楴杮਍‭畁楤ⵯ牰獥牥楶杮琠慲獮潣敤瀠灩汥湩൥ⴊ倠獯⵴潣癮牥楳湯挠湯楳瑳湥祣挠敨正൳ⴊ传瑰潩慮⁬敳潣摮瀠獡⁳潴爠灥慬散漠楲楧慮獬਍‭敍慴慤慴洠牡楫杮琠⁯敤整瑣愠牬慥祤瀠潲散獳摥映汩獥਍਍⌣圠慨⁴桔獩倠潲敪瑣䐠敯൳ഊ吊楨⁳牰橯捥⁴捳湡⁳⁡潦摬牥爠捥牵楳敶祬‬楦摮⁳楶敤⁯楦敬ⱳ愠摮挠湯敶瑲⁳桴浥琠⁯偍‴獵湩⁧䙆灭来മഊ䬊祥戠桥癡潩獲ഺⴊ䬠敥獰愠灳捥⁴慲楴൯ⴊ䄠潶摩⁳灵捳污湩⁧桷湥猠畯捲⁥污敲摡⁹楦獴琠牡敧⁴潢湵獤਍‭獕獥攠敶⁮楤敭獮潩獮爠煥極敲⁤祢䠠㈮㐶䠯㈮㔶攠据摯牥൳ⴊ倠敲敳癲獥愠摵潩眠敨⁮牰獥湥൴ⴊ嘠污摩瑡獥漠瑵異⁴瑳敲浡挠湯楳瑳湥祣愠瑦牥挠湯敶獲潩൮ⴊ匠灵潰瑲⁳汣慥畮⁰潷歲汦睯㩳਍†‭敄敬整漠楲楧慮獬愠瑦牥猠捵散獳畦⁬畯灴瑵瘠污摩瑡潩൮ ⴠ删灥慬散漠楲楧慮獬眠瑩⁨慶楬慤整⁤畯灴瑵൳ഊ⌊‣牐橯捥⁴瑓畲瑣牵൥ഊⴊ洠楡⹮祰›湅牴⁹潰湩ⱴ猠慴瑲⁳啇⁉牯䌠䥌਍‭敲畱物浥湥獴琮瑸›祐桴湯搠灥湥敤据敩൳ⴊ瘠摩潥牟獥穩牥振楬瀮㩹䌠䥌眠牯晫潬⁷湡⁤整浲湩污唠൉ⴊ瘠摩潥牟獥穩牥术極瀮㩹倠兹⁴啇⁉潷歲汦睯਍‭楶敤彯敲楳敺⽲捳湡敮⹲祰›楆敬搠獩潣敶祲愠摮瀠潲散獳摥洭牡敫⁲楦瑬牥湩൧ⴊ瘠摩潥牟獥穩牥支瑳浩瑡牯瀮㩹倠潲敢愠摮攠瑳浩瑡潩⁮潬楧ൣⴊ瘠摩潥牟獥穩牥瀯潲散獳牯瀮㩹䘠浆数⁧牴湡捳摯⁥湡⁤潣獮獩整据⁹档捥獫਍‭楶敤彯敲楳敺⽲汣慥敮⹲祰›汃慥畮⁰湡⁤敲汰捡ⵥ牯杩湩污⁳慰獳獥਍‭楶敤彯敲楳敺⽲潬杧牥瀮㩹䘠汩⽥潣獮汯⁥潬杧湩⁧敳畴൰ഊ⌊‣敒畱物浥湥獴਍਍‭楗摮睯⁳瀨楲慭祲琠獥整⁤汰瑡潦浲ഩⴊ倠瑹潨⁮⸳〱ഫⴊ䘠浆数⁧‫䙆牰扯⁥癡楡慬汢൥ഊ倊瑹潨⁮慰正条獥ഺⴊ映浦数ⵧ祰桴湯㴾⸰⸲രⴊ倠兹㙴㴽⸶⸷റഊ䤊獮慴汬ഺഊ怊恠潰敷獲敨汬਍楰⁰湩瑳污⁬爭爠煥極敲敭瑮⹳硴൴怊恠਍਍⌣䘠浆数⁧湡⁤䙆牰扯൥ഊ吊敨愠灰爠獥汯敶⁳䙆灭来䘯灆潲敢椠⁮桴獩漠摲牥ഺㄊ‮湅楶潲浮湥⁴癯牥楲敤瀠瑡൨㈊‮䅐䡔氠潯畫൰㌊‮潃浭湯圠湩敇⁴湩瑳污⁬潬慣楴湯਍⸴䘠污扬捡⁫潣浭湡⁤慮敭਍਍灏楴湯污攠癮物湯敭瑮漠敶牲摩獥ഺⴊ䘠䵆䕐彇䅐䡔਍‭䙆剐䉏彅䅐䡔਍਍晉礠畯⁲祳瑳浥倠呁⁈獩椠据湯楳瑳湥ⱴ猠瑥琠敨敳攠灸楬楣汴⹹਍਍⌣删湵楮杮琠敨䄠灰਍਍⌣‣啇⁉潍敤਍਍恠灠睯牥桳汥൬瀊瑹潨⁮慭湩瀮൹怊恠਍਍啇⁉楨桧楬桧獴ഺⴊ䴠摯牥⁮楬桧⁴桴浥൥ⴊ䘠汵⵬捳敲湥猠灵潰瑲ഺ ⴠ䈠瑵潴㩮䘠汵⁬捓敲湥਍†‭桓牯捴瑵›ㅆ‱潴杧敬਍†‭桓牯捴瑵›獅⁣硥瑩⁳畦汬猭牣敥൮ⴊ倠牥昭汩⁥牧灡楨慣⁬牰杯敲獳戠牡⁳湩匠慴畴⁳潣畬湭਍‭潃潬敲⁤湡⁤敲摡扡敬氠杯瀠湡汥戠⁹敬敶൬ⴊ䄠瑣慵⁬畯灴瑵猠穩⁥桳睯⁮晡整⁲慥档映汩⁥楦楮桳獥਍‭灏楴湯污椠据畬敤瀭潲散獳摥琠杯汧⁥畤楲杮猠慣൮ഊ⌊⌣䌠䥌䴠摯൥ഊ䜊湥牥污ഺഊ怊恠潰敷獲敨汬਍祰桴湯洠楡⹮祰ⴠ渭ⵯ畧⁩椼灮瑵摟物‾潛瑰潩獮൝怊恠਍਍效灬ഺഊ怊恠潰敷獲敨汬਍祰桴湯洠楡⹮祰ⴠ渭ⵯ畧⁩ⴭ敨灬਍恠ൠഊ⌊‣畑捩⁫慍畮污਍਍⌣‣敒畣獲癩⁥捓湡䈠桥癡潩൲ഊⴊ吠敨猠汥捥整⁤湩異⁴潦摬牥椠⁳捳湡敮⁤敲畣獲癩汥⹹਍‭汁⁬畳灰牯整⁤楶敤⁯楦敬⁳湩猠扵楤敲瑣牯敩⁳牡⁥湩汣摵摥മഊ⌊⌣倠潲散獳摥䘭汩⁥敄整瑣潩⁮䴨瑥摡瑡⥡਍਍‭潃癮牥整⁤畯灴瑵⁳牡⁥慴杧摥眠瑩⁨敭慴慤慴洠牡敫㩲਍†‭楶敤彯敲楳敺彲牰捯獥敳㵤റⴊ䘠汩獥眠瑩⁨桴獩洠牡敫⁲牡⁥歳灩数⁤祢搠晥畡瑬琠⁯牰癥湥⁴捡楣敤瑮污爠ⵥ牰捯獥楳杮മⴊ传敶牲摩⁥桷湥渠敥敤㩤਍†‭䱃㩉甠敳ⴠ椭据畬敤瀭潲散獳摥਍†‭啇㩉攠慮汢⁥湉汣摵⁥污敲摡⁹牰捯獥敳൤ഊ⌊⌣䐠汥瑥⁥牏杩湩污⁳獶删灥慬散传楲楧慮獬਍਍‭敄敬整漠楲楧慮獬愠瑦牥瀠潲散獳湩㩧਍†‭敋灥⁳敲楳敺⁤畯灴瑵⁳獡猠灥牡瑡⁥楦敬⹳਍†‭敒潭敶⁳牯杩湩污映汩獥愠瑦牥栠慥瑬⁨慶楬慤楴湯മഊⴊ匠捥湯⁤慰獳›敲汰捡⁥牯杩湩污⁳楷桴爠獥穩摥ഺ ⴠ嘠污摩瑡獥爠獥穩摥漠瑵異獴മ ⴠ䐠汥瑥獥漠楲楧慮⁬楦敬⹳਍†‭敒慮敭⁳敲楳敺⁤楦敬⁳慢正琠⁯桴⁥牯杩湩污映汩湥浡獥മ ⴠ䈠獥⁴灯楴湯眠敨⁮潹⁵慷瑮映湩污映汩獥琠⁯敫灥漠楲楧慮⁬慮敭⹳਍਍⌣䌠䥌传瑰潩獮਍਍‭湩異彴楤൲ ⴠ删煥極敲⹤删潯⁴楤敲瑣牯⁹潴猠慣⁮敲畣獲癩汥⹹਍਍‭ⴭ敲潳畬楴湯圠䡸਍†‭慔杲瑥戠畯摮湩⁧潢ⱸ搠晥畡瑬›㈱〸㝸〲മ ⴠ丠⁯灵捳污湩⁧晩猠畯捲⁥污敲摡⁹楦獴മ ⴠ倠牯牴楡⁴潳牵散⁳牡⁥慨摮敬⁤祢漠楲湥慴楴湯愭慷敲戠畯摮⹳਍਍‭ⴭ牤⵹畲൮ ⴠ倠潲敢⬠攠瑳浩瑡⁥湯祬‬潮瀠潲散獳湩⹧਍਍‭ⴭ汣慥畮൰ ⴠ䄠瑦牥瀠潲散獳湩Ⱨ搠汥瑥⁥牯杩湩污⁳桷湥瘠污摩瑡摥爠獥穩摥猠扩楬杮椠⁳敨污桴⹹਍਍‭ⴭ敲汰捡ⵥ牯杩湩污൳ ⴠ匠捥湯⁤慰獳›敤敬整漠楲楧慮⁬桴湥爠湥浡⁥慶楬慤整⁤敲楳敺⁤楦敬琠⁯牯杩湩污渠浡⹥਍†‭畍畴污祬攠捸畬楳敶眠瑩⁨ⴭ汣慥畮⹰਍਍‭ⴭ湩汣摵ⵥ牰捯獥敳൤ ⴠ䤠据畬敤映汩獥洠牡敫⁤獡愠牬慥祤瀠潲散獳摥椠⁮敭慴慤慴മ ⴠ䈠⁹敤慦汵ⱴ洠牡敫⁤楦敬⁳牡⁥歳灩数⹤਍਍‭ⴭ牣⁦ൎ ⴠ䌠湯瑳湡⁴慒整䘠捡潴⁲潦⁲畱污瑩⽹楳敺琠慲敤景ⱦ搠晥畡瑬›㘲മഊⴊⴠ挭摯捥笠㉨㐶栬㘲紵਍†‭楖敤⁯潣敤⁣档楯散മഊⴊⴠ氭杯昭汩⁥䅐䡔਍†‭潌⁧慰桴‬敤慦汵㩴瘠摩潥牟獥穩牥氮杯椠⁮畣牲湥⁴楤敲瑣牯⹹਍਍⌣倠潲散獳湩⁧湡⁤慖楬慤楴湯倠灩汥湩൥ഊ䘊牯攠捡⁨楦敬ഺㄊ‮牐扯⁥潳牵散洠摥慩਍⸲䌠浯異整漠瑵異⁴楤敭獮潩獮਍⸳䔠据摯⁥楷桴䘠浆数൧㐊‮畒⁮潰瑳挭湯敶獲潩⁮潣獮獩整据⁹档捥獫਍਍潃獮獩整据⁹档捥獫椠据畬敤ഺⴊ传瑵異⁴慨⁳⁡楶敤⁯瑳敲浡਍‭晉椠灮瑵栠摡愠摵潩‬畯灴瑵洠獵⁴慨敶愠摵潩਍‭畄慲楴湯搠汥慴猠慴獹眠瑩楨⁮潴敬慲据൥ഊ䤊⁦档捥⁫慦汩㩳਍‭楆敬椠⁳慭歲摥愠⁳牥潲൲ⴊ䔠牲牯椠⁳桳睯⁮爨摥椠⁮䱃⥉਍‭牅潲⁲獩氠杯敧൤ഊ䤊⁦畯灴瑵愠牬慥祤攠楸瑳㩳਍‭硅獩楴杮漠瑵異⁴獩瘠污摩瑡摥਍‭楆敬椠⁳慭歲摥愠⁳歳灩数⁤瘨污摩瑡摥ഩഊ⌊‣敍慴慤慴䴠牡敫⁲潦⁲牐捯獥敳⁤楆敬൳ഊ吊⁯畳灰牯⁴敲慮敭⁤畯灴瑵⁳眨敨敲张敲楳敺⁤獩爠浥癯摥Ⱙ挠湯敶瑲摥漠瑵異獴愠敲琠条敧⁤楷桴洠瑥摡瑡㩡਍਍‭楶敤彯敲楳敺彲牰捯獥敳㵤റഊ匊慣湮牥戠桥癡潩㩲਍‭敄慦汵㩴猠楫獰映汩獥眠瑩⁨桴獩洠牡敫൲ⴊ传敶牲摩㩥ⴠ椭据畬敤瀭潲散獳摥⠠䱃⥉漠⁲湉汣摵⁥污敲摡⁹牰捯獥敳⁤䜨䥕ഩഊ吊楨⁳污潬獷爠ⵥ畲⁮慳敦祴攠敶⁮晡整⁲敳潣摮瀭獡⁳敲慮敭眠牯晫潬獷മഊ⌊‣敓潣摮倠獡⁳潗歲汦睯൳ഊ⌊⌣䌠敬湡灵਍਍‭敋灥⁳敲楳敺⁤楦敬⁳獡猠灥牡瑡⁥畯灴瑵൳ⴊ䐠汥瑥獥漠楲楧慮⁬楦敬⁳晡整⁲敨污桴⵹畯灴瑵瘠污摩瑡潩൮ഊ⌊⌣删灥慬散传楲楧慮獬਍਍‭慖楬慤整⁳敲楳敺⁤畯灴瑵൳ⴊ䐠汥瑥獥漠楲楧慮⁬楦敬൳ⴊ删湥浡獥爠獥穩摥映汩獥琠⁯牯杩湩污渠浡獥਍‭湉汣摵獥圠湩潤獷猭晡⁥敤敬楴湯栠湡汤湩⁧爨慥ⵤ湯祬爠浥癯污⬠爠瑥祲ഩഊ⌊‣潌杧湩൧ഊ䌊䥌ഺⴊ䐠祲爭湵›潣獮汯⁥‫楦敬氠杯楧杮਍‭敒污瀠潲散獳湩㩧瀠潲牧獥⵳牤癩湥琠牥業慮⁬畯灴瑵‬潬⁧楦敬爠捥牯獤搠瑥楡獬਍਍啇㩉਍‭楒档挠汯牯摥氠杯⁳祢氠癥汥椠⁮潬⁧慰敮਍‭潌⁧楦敬猠楴汬爠捥牯獤愠汬攠敶瑮൳ഊ⌊‣潃浭湯吠潲扵敬桳潯楴杮਍਍⌣‣䙆牰扯⽥䙆灭来渠瑯映畯摮漠⁲慦汩湩൧ഊⴊ䤠獮慴汬䘠浆数⽧䙆牰扯൥ⴊ匠瑥䘠䵆䕐彇䅐䡔愠摮䘠偆佒䕂偟呁⁈硥汰捩瑩祬椠⁦敮摥摥਍‭敖楲祦戠湩牡敩⁳畲⁮慭畮污祬ഺഊ怊恠潰敷獲敨汬਍晦灭来ⴠ敶獲潩൮昊灦潲敢ⴠ敶獲潩൮怊恠਍਍⌣‣畁楤⁯業獳湩⁧湩漠瑵異൴ഊⴊ䌠牵敲瑮瀠灩汥湩⁥硥汰捩瑩祬洠灡⁳畡楤⁯桷湥瀠敲敳瑮਍‭潃獮獩整据⁹档捥獫渠睯映楡⁬潣癮牥楳湯椠⁦湩異⁴畡楤⁯楤慳灰慥獲਍਍⌣‣捁散獳搠湥敩⁤湯挠敬湡灵爯灥慬散਍਍‭汃獯⁥楦敬攠灸潬敲獲瀯慬敹獲甠楳杮琠敨映汩൥ⴊ䔠獮牵⁥汣畯⁤祳据琠潯獬愠敲渠瑯氠捯楫杮映汩獥਍‭敒牴⁹灯牥瑡潩⁮挨敬湡灵栠獡圠湩潤獷爠瑥祲栠湡汤湩⥧਍਍⌣‣啇⁉潤獥渠瑯猠潨⁷敮敷瑳挠慨杮獥਍਍‭汃獯⁥污⁬汯⁤灡⁰楷摮睯൳ⴊ删汥畡据⁨牦浯甠摰瑡摥瀠潲敪瑣映汯敤൲ഊ⌊‣敄敶潬浰湥⁴潎整൳ഊ刊湵映潲⁭牰橯捥⁴潲瑯ഺഊ怊恠潰敷獲敨汬਍祰桴湯洠楡⹮祰਍祰桴湯洠楡⹮祰ⴠ渭ⵯ畧⁩楶敤獯ⴠ搭祲爭湵਍恠ൠഊ匊杵敧瑳摥琠獥⁴慭牴硩ഺⴊ䰠湡獤慣数猠畯捲獥਍‭潐瑲慲瑩猠畯捲獥਍‭楗桴愠摮眠瑩潨瑵愠摵潩਍‭硅獩楴杮漠瑵異獴瀠敲敳瑮਍‭敒汰捡ⵥ牯杩湩污⁳汦睯਍਍⌣嘠牥楳湯湩൧ഊ䌊牵敲瑮椠瑮湥敤⁤敲敬獡⁥慴杲瑥›⸱⸰രഊ圊敨⁮牰灥牡湩⁧敲敬獡⁥牡楴慦瑣⁳䔨䕘⬠椠獮慴汬牥Ⱙ欠敥⁰桴獩删䅅䵄⁅獡猠畯捲ⵥ景琭畲桴戠桥癡潩⁲潤畣敭瑮瑡潩⹮਍਍⌣䈠極摬䔠䕘愠摮䤠獮慴汬牥਍਍⌣‣潌慣⁬塅⁅畢汩⁤在湩潤獷ഩഊ䘊潲⁭牰橯捥⁴潲瑯ഺഊ怊恠潰敷獲敨汬਍祰桴湯ⴠ⁭楰⁰湩瑳污⁬爭爠煥極敲敭瑮⵳敤⹶硴൴瀊睯牥桳汥⁬䔭數畣楴湯潐楬祣䈠灹獡⁳䘭汩⁥尮捳楲瑰屳畢汩彤硥⹥獰റ怊恠਍਍畏灴瑵ഺⴊ搠獩屴楖敤副獥穩牥瑓摵潩噜摩潥敒楳敺卲畴楤⹯硥൥ഊ⌊⌣䰠捯污椠獮慴汬牥戠極摬⠠楗摮睯⥳਍਍敒畱物浥湥獴ഺⴊ䤠湮⁯敓畴⁰‶湩瑳污敬⁤䤨䍓⹃硥⁥癡楡慬汢⥥਍਍畂汩⁤潣浭湡㩤਍਍恠灠睯牥桳汥൬瀊睯牥桳汥⁬䔭數畣楴湯潐楬祣䈠灹獡⁳䘭汩⁥尮捳楲瑰屳畢汩彤湩瑳污敬⹲獰‱䄭灰敖獲潩⁮⸱⸰ര怊恠਍਍畏灴瑵ഺⴊ搠獩屴湩瑳污敬屲楖敤副獥穩牥瑓摵潩匭瑥灵ㄭ〮〮攮數਍਍⌣䜠瑩畈⁢敒敬獡⁥畁潴慭楴湯⠠ㅶ〮〮ഩഊ圊牯晫潬⁷楦敬ഺⴊ⸠楧桴扵眯牯晫潬獷爯汥慥敳礮汭਍਍敂慨楶牯ഺⴊ吠楲杧牥›異桳琠条洠瑡档湩⁧⩶਍‭畂汩獤瀠牯慴汢⁥塅⁅稨灩 湡⁤湩瑳污敬⁲湯眠湩潤獷氭瑡獥൴ⴊ倠扵楬桳獥戠瑯⁨牡楴慦瑣⁳潴䜠瑩畈⁢敒敬獡൥ഊ䔊灸捥整⁤敲敬獡⁥牡楴慦瑣㩳਍‭楖敤副獥穩牥瑓摵潩瘭⸱⸰ⴰ楷㙮⸴楺൰ⴊ嘠摩潥敒楳敺卲畴楤ⵯ敓畴⵰ㅶ〮〮攮數਍਍⌣‣楆獲⵴楴敭䜠瑩猠瑥灵⠠晩渠敥敤⥤਍਍晉琠楨⁳潦摬牥椠⁳潮⁴敹⁴⁡楧⁴敲潰楳潴祲ഺഊ怊恠潰敷獲敨汬਍楧⁴湩瑩਍楧⁴摡⁤മ朊瑩挠浯業⁴洭∠敒敬獡⁥牰灥瘠⸱⸰∰਍楧⁴牢湡档ⴠ⁍慭湩਍楧⁴敲潭整愠摤漠楲楧⁮礼畯⵲楧桴扵爭灥ⵯ牵㹬਍楧⁴異桳ⴠ⁵牯杩湩洠楡൮怊恠਍਍牃慥整愠摮瀠獵⁨敲敬獡⁥慴㩧਍਍恠灠睯牥桳汥൬朊瑩琠条瘠⸱⸰ര朊瑩瀠獵⁨牯杩湩瘠⸱⸰ര怊恠਍਍晁整⁲慴⁧異桳‬楇䡴扵䄠瑣潩獮眠汩⁬畢汩⁤湡⁤異汢獩⁨桴⁥敲敬獡⁥畡潴慭楴慣汬⹹਍਍⌣䰠捩湥敳਍਍摁⁤潹牵瀠敲敦牲摥氠捩湥敳映汩⁥敢潦敲瀠扵楬⁣敲敬獡⹥਍# batch-video-resizer਍ഀ
਍