---
name: creo-modeling
description: Drive PTC Creo Parametric on the user's Windows PC through the creo-modeling MCP server (CREOSON). Use when asked to open a Creo template, change named parameters or dimensions, regenerate, save a variant under a new name, export STEP or PDF, or batch shaft, flange, or bushing variants from a CSV.
---

# Creo modeling

Use the `creo-modeling` MCP tools. They talk to CREOSON on this PC (Creo Parametric 12.4.4.0, CREOSON 3.0.2 at `C:\CREOSON`, port 9056). Do not invent Creo menu clicks or shell commands that drive Creo directly.

Tool errors are written in Chinese so the teacher can read them. Translate the meaning, and show the original sentence when a step fails.

## Safety

- Call `session_status` before any edit. If `creoson` cannot be reached, stop and tell the user to start CREOSON from `C:\CREOSON` (CreosonSetup, port 9056) and leave that window open.
- If `creo_running` is false, ask the user to open Creo. Call `start_creo` only when they give a full path whose file name is `nitro_proe_remote.bat`. CREOSON rejects every other name.
- Keep the template file. Variants go through `save_as_copy` or `batch_from_csv`.
- `save_model` overwrites the open file. Call it only after the user explicitly asks to overwrite that file, and pass `confirm_overwrite` true.
- `save_as_copy` refuses when the new name is already in Creo's working directory, unless the user explicitly agrees to replace it (`confirm_overwrite` true).
- There is no erase or delete tool. Do not look for one, and do not ask CREOSON to erase models from the session.
- `set_parameter` will not create a parameter that the template does not already have.

## Workflow

1. `session_status`.
2. `set_working_directory` to the folder that holds the template, or pass a full path to `open_model`.
3. `open_model` with the template, for example `D:\lab\shaft.prt`.
4. `list_parameters` and confirm the names match the request (`D`, `L`, `OD`, …).
5. `set_parameter` for each change. Send real dimensions as decimals (`20.0` or the string `"20.0"`) so they go out as DOUBLE. A whole number such as `4` is INTEGER (hole counts). `true` / `false` is BOOL. Other text is STRING.
6. `regenerate`. If this fails, stop. Do not save a model that did not regenerate.
7. `save_as_copy` with a new file name only, such as `shaft_d20_l80`. The tool adds `.prt` when the source is a part. The original file stays on disk.
8. After `save_as_copy`, the in-session model has the new name. `open_model` the template again before the next variant.
9. `export_model` with `kind` `STEP` for a part, or `PDF` for a drawing (`.drw`).

`batch_from_csv` does steps 3–7 for every data row. The CSV must have a `variant` column plus one column per Creo parameter. See `examples/shaft_variants.csv`.

## Names

- Parameter names match the Creo parameter exactly. This project uses uppercase: `D`, `L`, `C`, `OD`, `ID`, `T`, `PCD`, `N`, `MARK`.
- File names start with a letter and use letters, digits, underscores, or hyphens. No spaces or Chinese in the file name.
- Put the driving sizes in the file name: `shaft_d20_l80`, `flange_od80_id40`, `bushing_od20_id16_l30`.

## Prefer parameters over dimensions

A drawing template should drive geometry with relations, for example `d0 = D`. `set_dimension` on `d0` is overwritten the next time the model regenerates. Change `D` with `set_parameter`, then `regenerate`.

Use `list_dimensions` only to read symbols or to edit a one-off dimension that is not driven by a relation.

## Examples

### Shaft

Template parameters: `D` diameter, `L` length, `C` chamfer (all reals), `MARK` string.

Relations: `d0 = D`, `d1 = L`, `d2 = C` (use the symbols shown on the model).

One variant:

- `set_parameter` `D` = `20.0`, `L` = `80.0`, `C` = `1.0`, `MARK` = `A`
- `regenerate`
- `save_as_copy` `shaft_d20_l80`

Three variants from `examples/shaft_variants.csv`:

- `batch_from_csv` with that CSV path and the template path.

### Flange

Parameters: `OD` outer diameter, `ID` bore, `T` thickness, `PCD` bolt-circle diameter (reals), `N` bolt-hole count (integer).

```csv
variant,OD,ID,T,PCD,N
flange_od80,80.0,40.0,12.0,65.0,4
flange_od100,100.0,50.0,14.0,80.0,6
```

`N` has no decimal point, so it is sent as INTEGER. The diameters use decimals.

### Bushing

Parameters: `OD` outer diameter, `ID` inner diameter, `L` length, all reals.

```csv
variant,OD,ID,L
bushing_20x16x30,20.0,16.0,30.0
bushing_25x20x40,25.0,20.0,40.0
```

## Pitfalls

- CREOSON and Creo are different programs. CREOSON can be up while Creo is closed. `session_status` reports both.
- Opening `shaft.prt` uses Creo's working directory when the path has no folder. If the file is elsewhere, pass the full path. `file_open` receives the file name and the folder separately; the tools already split that.
- `save_as_copy` renames the model in memory (`file_rename` with `onlysession` true) and then saves. The previous file remains on disk, but it is no longer the active model.
- The command-line `python -m creo_modeling batch` still stops after regenerate and does not save. Use the MCP tool `batch_from_csv` when the user wants files written.
- On connect, once Creo is running, the server calls `creo_set_creo_version` (default 12, override with `CREO_VERSION`). creopyson 0.7.8's own docstring still mentions versions 7–9; the call only sends the integer, which CREOSON 3.0.2 needs so regenerate on Creo 12 does not use a retired config option.
- PDF export is for drawings. If a part PDF fails, export STEP or open the drawing and export that.
- Excel CSV must be comma-separated UTF-8. A missing `variant` column usually means the file was saved with semicolons.
