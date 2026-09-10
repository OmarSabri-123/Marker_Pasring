# Marker Parsing

Document-to-Markdown conversion built on
[Marker](https://github.com/datalab-to/marker).

## Requirements

- Windows 10 or Windows 11 (64-bit)
- [Python 3.13 (64-bit)](https://www.python.org/downloads/) with the Python
  launcher and `Add python.exe to PATH` enabled during installation
- Internet access for package and model downloads
- Sufficient free disk space for Marker/Surya model files
- Optional GPU acceleration: an NVIDIA CUDA-capable GPU with a current
  [NVIDIA driver](https://www.nvidia.com/Download/index.aspx)

This project currently requires `marker-pdf>=1.8,<2.0`. The tested environment
uses Marker 1.10.2 and PyTorch 2.11.0 with CUDA 12.8.

The virtual-environment name used throughout this project is `.venv313`.
Do not copy an existing `.venv313` directory to another computer. Copy the
project files and create a new `.venv313` environment on that machine.

## Windows setup (Command Prompt)

Open **Command Prompt (`cmd.exe`)**, then change to the copied project directory:

```cmd
cd /d C:\path\to\Marker_Pasring
```

Confirm that Python 3.13 is installed:

```cmd
py -3.13 --version
```

Create and activate the `.venv313` virtual environment:

```cmd
py -3.13 -m venv .venv313
.venv313\Scripts\activate.bat
python --version
python -m pip install --upgrade pip setuptools wheel
```

After activation, `python --version` must report Python 3.13.x.

If the `py` command is unavailable, verify that `python --version` reports
Python 3.13.x and create the same environment with:

```cmd
python -m venv .venv313
.venv313\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
```

### NVIDIA GPU installation

First confirm that Windows can see the NVIDIA GPU:

```cmd
nvidia-smi
```

Install the CUDA-enabled PyTorch build from the official
[PyTorch CUDA 12.8 wheel index](https://download.pytorch.org/whl/cu128)
**before** installing the remaining requirements:

```cmd
python -m pip install "torch==2.11.0+cu128" --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
```

Verify that PyTorch can use the GPU:

```cmd
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA runtime:', torch.version.cuda); print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
```

`CUDA available` must print `True`. The CUDA runtime is included in the
PyTorch wheel; a separate CUDA Toolkit installation is normally unnecessary.
An up-to-date NVIDIA driver is still required.

### CPU-only installation

On a computer without a supported NVIDIA GPU, install directly from the
requirements file:

```cmd
python -m pip install -r requirements.txt
```

CPU conversion works but OCR and balanced-mode conversion can be much slower.

### Make the source package available

This repository currently has no `pyproject.toml` or `setup.py`, so it cannot
be installed with `pip install -e .`. Set `PYTHONPATH` to the `src` directory
in every new Command Prompt session:

```cmd
set "PYTHONPATH=%CD%\src"
python -m pdf2md --help
```

## Optional: download models before conversion

Marker downloads its models automatically on first use. To download the main
models ahead of time with resume support, run the included PowerShell script
from Command Prompt:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File ".\fetch_models.ps1"
```

Check model-download status with:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File ".\fetch_models.ps1" -Status
```

## Run the converter

For each new Command Prompt window:

```cmd
cd /d C:\path\to\Marker_Pasring
.venv313\Scripts\activate.bat
set "PYTHONPATH=%CD%\src"
```

GPU conversion with higher-quality formatting:

```cmd
set "TORCH_DEVICE=cuda"
python -m pdf2md "pdfs\document.pdf" --langs en --mode balanced --verbose
```

Force OCR only when the PDF is scanned or its existing text is corrupted:

```cmd
python -m pdf2md "document.pdf" --langs en --force-ocr --mode balanced --verbose
```

Faster conversion for a PDF that already contains selectable text:

```cmd
python -m pdf2md "document.pdf" --langs en --mode fast --no-images --verbose
```

## Output layout

Each document gets its own folder under `files/`, named after the PDF:

```text
files/document/
    document.md              # converted Markdown document
    _page_0_Picture_3.jpeg   # images, named by absolute PDF page
    _page_103_Picture_0.jpeg
```

Use `-o` to select an exact output file, or `--output-dir` to change the root
(default `./files`, or `$PDF2MD_OUTPUT_DIR`):

```cmd
python -m pdf2md "document.pdf" -o "files\document\document.md" --mode balanced
```

## Other file formats

Marker accepts more than PDFs, and dispatches on the file itself:

```cmd
python -m pdf2md "report.docx"
python -m pdf2md "slides.pptx"
python -m pdf2md "book.epub"
python -m pdf2md "scan.png"
```

Supported: `.pdf .docx .pptx .xlsx .epub .html .png .jpg .jpeg .webp .gif .tiff`

`--pages` applies to PDFs. Other supported files are converted in one pass.

## PDF batching

PDFs are processed in batches of 32 pages by default and merged into one
Markdown file. Change the size when needed:

```cmd
python -m pdf2md "document.pdf" --batch-size 16 --mode balanced
```

The models stay loaded between batches. Each finished batch is written to a
`.batches/` folder next to the Markdown file, so an interrupted command
continues where it stopped instead of converting the whole document again:

```text
files/document/
    document.md
    .batches/
        manifest.json            # source fingerprint and finished batches
        pages_0000-0031.md
```

Rerun the same command to resume. Batches are reused only when the source file
and the conversion settings are unchanged; editing the PDF or changing
`--mode`, `--pages`, `--langs`, `--force-ocr`, or `--batch-size` converts the
document again from the start. Use `--no-resume` to ignore the cache, and
delete `.batches/` when the document is finished and the cache is no longer
wanted.

**Windows prerequisite for Office and EPUB files:** WeasyPrint needs the
GTK/Pango libraries, which are not part of its wheel. Without them these
formats fail with a message telling you so. Install the
[GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases),
reopen the terminal, and retry. Saving the document as PDF from Word and
converting that PDF needs no extra installation, and usually preserves the
layout better.

## Non-English documents

Pass OCR language hints with `--langs`, for example Arabic:

```cmd
python -m pdf2md "document.pdf" --langs ar --force-ocr --mode balanced
```

Use `--langs ar,en` for mixed documents. Surya recognizes Arabic script, but
neither Surya nor Marker applies right-to-left reading-order handling, so
proofread the output of a right-to-left document. Convert two or three pages
with `--pages "0-2"` before committing to a whole book.

Other useful options:

```cmd
python -m pdf2md "document.pdf" --pages "0-4,7" --langs en
python -m pdf2md --help
```

`--pages` is 0-indexed.

`--mode balanced` enables additional OCR-assisted line formatting.
`--mode fast` uses Marker's lighter path. If `--mode` is omitted, this project
selects balanced mode on CUDA and fast mode on CPU/MPS.

## Use as a library

```python
from pdf2md import ConverterSettings, PdfToMarkdownConverter

converter = PdfToMarkdownConverter(ConverterSettings(save_images=True))
result = converter.convert("document.pdf")
print(result.markdown_path)
```

Models are loaded once per `PdfToMarkdownConverter` instance and reused across
calls. Keep one converter instance alive when converting multiple files. A new CLI command
starts a new process and therefore reloads the models.

## Project layout

```text
src/pdf2md/
    cli.py         # Command-line arguments and startup
    config.py      # User settings and Marker configuration
    converter.py   # Conversion workflow and Marker integration
    exceptions.py  # Conversion exceptions
pdfs/              # Input documents
files/             # Converted output, one folder per document
```

Deactivate the environment when finished:

```cmd
deactivate
```
