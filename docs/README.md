# SIOT Pico Bot 2 Docs

This directory is the root-level Sphinx documentation site for this repository.

The canonical source root for the current docs build is `docs/`.

The nested `docs/docs/` subtree already exists locally as an older starter scaffold.
It is intentionally left in place in this patch and is excluded from the Sphinx build.

## Build locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r docs/requirements.txt
python3 -m sphinx -W -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser after a successful build.

## Scope of this first pass

- current firmware and hardware only
- manual API pages only
- no autodoc
- no docs deployment config in this patch

## Source material

The current pages are grounded in the tracked repository files, especially:

- `README.md`
- `main.py`
- `config.py`
- `robot.py`
- `hal/`
- `tasks/`
- `safety/`
- `gates/`
- `tools/test-dashboard.html`
