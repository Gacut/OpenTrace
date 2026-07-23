# OpenTrace
<img width="1983" height="793" alt="OpenTraceBaner" src="https://github.com/user-attachments/assets/560ccaea-c76b-4847-be24-cfc06c7ed107" />

OpenTrace is a private-by-design, offline desktop workspace for organizing
OSINT investigations. It provides a visual investigation board without
accounts, cloud synchronization, telemetry, or mandatory online services.

> OpenTrace is an organizational and analytical tool. Users are responsible
> for complying with applicable laws, platform terms, and ethical standards.

## Highlights

- Infinite visual board with text notes, images, pins, and directional
  relationships
- Editable relationship labels, colors, arrows, and branched connections
- Tasks, verification queue, sources, hypotheses, and an investigation journal
- OSINT properties, tags, classifications, source URLs, aliases, and SHA-256
  integrity information
- Search across materials, journal entries, and UUID identifiers
- Global, user-managed OSINT tool library shared between investigations
- Automatic saving, undo/redo, layers, saved camera state, and board navigation
- Portable investigation folders with ZIP packaging and extraction
- PNG and structured JSON export
- Polish and English user interface
- Fully offline operation with no telemetry
  
<img width="780" height="449" alt="opentraceprogram" src="https://github.com/user-attachments/assets/951f53fe-7f61-4094-9dc0-1934bedea400" />

## Requirements

- Python 3.12
- PySide6 6.11.1

## Running from source

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m app
```

On Linux, activate the environment with:

```bash
source .venv/bin/activate
```

The source code is designed to be cross-platform, but the downloadable 1.0.0
binary release currently targets Windows x64.

## Tests

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest
```

The GitHub Actions test workflow runs the suite on both Windows and Ubuntu.

## Building the Windows application

```powershell
python -m pip install -e .[dev]
pyinstaller --clean --noconfirm opentrace.spec
```

The application is created in `dist/OpenTrace/`. The release workflow runs the
tests, builds this directory on a Windows runner, adds the licensing files,
creates a ZIP archive, calculates its SHA-256 checksum, and publishes both as
GitHub Release assets.

## Investigation data

An investigation is a regular portable directory. SQLite stores its metadata,
while imported images are copied into the investigation's `media/` directory.
Paths stored in the database are relative.

The global OSINT tool library is stored in the user's application configuration
directory and is intentionally independent of individual investigations.

## Privacy and network behavior

OpenTrace does not send telemetry and does not automatically query external
services. URLs explicitly opened by the user are passed to the system's default
web browser.

## License

OpenTrace is released under the [MIT License](LICENSE).

The standalone distribution includes Qt for Python components used under
LGPLv3. Third-party notices, complete license texts, corresponding-source
information, and relinking instructions are available in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) and the
[`licenses/`](licenses/) directory.

## Author

Created by [Gacut](https://github.com/Gacut) with
[OpenAI Codex](https://openai.com/codex/).
