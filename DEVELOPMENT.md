# Development Guide

This guide is for contributors and engineers who want to modify the source code of BLACKICE.

## Prerequisites

- Python 3.10+
- `pip`
- `venv` (recommended)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mihirmaru22/BLACKICE.git
   cd BLACKICE
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install build twine  # For packaging
   ```

## Running Tests

We use `unittest` for the core test suite.

```bash
python scripts/test_blackice.py
```

## Project Structure

- `src/blackice/`: Core package source code.
- `scripts/`: Executable scripts and tests.
- `configs/`: Default configuration files.
- `notebooks/`: Jupyter notebooks for data analysis.

## Packaging

To build a new version of the package:

1. **Update version**  
   Edit `version` in `pyproject.toml` and `__version__` in `src/blackice/__init__.py`.

2. **Build artifacts**
   ```bash
   rm -rf dist/
   python -m build
   ```

3. **Publish to PyPI**
   ```bash
   twine upload dist/*
   ```

## Design Principles

When contributing, please adhere to these core principles:

1. **Zero External Logic Dependencies**: The core math engine (`baseline.py`) should rely only on Python primitives or `numpy` if absolutely necessary. Avoid heavy ML frameworks.
2. **Constant Memory**: All processing logic must be safe for infinite streams. Do not accumulate history indefinitely.
3. **Type Hints**: Use type hints (`typing.List`, `typing.Optional`) for all function signatures.
