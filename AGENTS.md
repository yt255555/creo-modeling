# AGENTS.md

Read this before changing the repo. The teacher-facing guide is `README.md` (简体中文). The guide for driving Creo is `SKILL.md`.

## What this project is

A small Python package that lets other AI agents operate PTC Creo Parametric on the user's Windows PC.

- Creo Parametric 12.4.4.0
- CREOSON 3.0.2 at `C:\CREOSON`, port 9056
- Python 3.12 (the package requires 3.10+)
- `creopyson` 0.7.8 talks to CREOSON
- An MCP server exposes that client over stdio

CREOSON needs Creo's install option **Object TOOLKIT Java and J-Link** (`pfcasync.jar`).

## Layout

```
src/creo_modeling/
  client.py       thin creopyson wrapper; the only place that calls creopyson
  tools.py        safe operations used by MCP (no erase/delete)
  mcp_server.py   MCP server, stdio, python -m creo_modeling.mcp_server
  params.py       CSV parameter tables
  batch.py        CLI batch; regenerates and does not save
  cli.py          python -m creo_modeling
examples/         sample CSV and the template note; no .prt files
tests/            mocked; Creo is not required
SKILL.md          how an agent should use the MCP tools
```

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Tests replace creopyson or `CreosonClient` with fakes. Do not start CREOSON, do not open Creo, and do not add network calls to tests.

Also useful locally:

```bash
python -m creo_modeling validate examples/shaft_variants.csv
python -m creo_modeling batch examples/shaft_variants.csv --template shaft.prt --dry-run
```

## Coding conventions

- Write code a programming beginner can read. Short functions, plain names, few layers.
- Comments, CLI text, and tool errors are 简体中文. MCP tool docstrings (the text other agents read) stay English.
- Do not guess creopyson method names. Match creopyson 0.7.8. The list in the `client.py` module docstring is the checked set. The constructor argument is `ip_adress` (the library's spelling).
- New Creo actions: add a one-line method on `CreosonClient`, a checked function in `tools.py`, a tool in `mcp_server.py`, and a mock test.
- Do not expose `file_erase`, `file_erase_not_displayed`, `creo_delete_files`, or `creo_rmdir`.
- `save_model` must keep refusing until `confirm_overwrite` is true.
- There is no creopyson `save_as`. A copy is `file_rename(..., onlysession=True)` then `file_save` of the new name.
- The MCP process owns stdout. Do not `print` from `mcp_server.py` or from code it imports on the success path. Errors for humans go to stderr only when the process cannot even start.
- Do not commit Creo binaries, `*.prt.N` version files, `trail.txt*`, or `std.out`.

## MCP entry

```bash
python -m creo_modeling.mcp_server
```

Environment: `CREOSON_HOST` (default `localhost`), `CREOSON_PORT` (default `9056`), `CREO_VERSION` (default `12`).
