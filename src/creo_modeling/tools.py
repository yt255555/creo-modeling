"""给 MCP 用的 Creo 操作。

这里决定哪些动作允许做。真正发请求的仍是 client.py 里的薄封装。
会删模型、清会话、删磁盘文件的 CREOSON 函数不在这里出现。
"""

import os

from creo_modeling.client import CreosonError, model_filename
from creo_modeling.params import load_parameter_table, parse_cell

# 给人和智能体看的失败说明。CREOSON 没启动时统一用这一句。
CREOSON_DOWN = (
    "连不上 CREOSON。请到 C:\\CREOSON 打开 CreosonSetup，"
    "确认端口是 9056，按下 Start CREOSON，并保持那个窗口开着。"
    "然后打开 Creo Parametric。"
)

_PARAM_TYPES = {"STRING", "DOUBLE", "INTEGER", "BOOL", "NOTE"}


def creo_version_from_env():
    """本机默认是 Creo 12。可用环境变量 CREO_VERSION 改。"""
    raw = os.environ.get("CREO_VERSION", "12")
    try:
        return int(raw)
    except ValueError as exc:
        raise CreosonError("环境变量 CREO_VERSION 必须是整数，例如 12。") from exc


def connect_session(client):
    """连上 CREOSON。服务器没开时抛出带中文说明的 CreosonError。"""
    try:
        if client._client is None:
            client.connect()
        return client._require()
    except ConnectionError as exc:
        client.disconnect()
        raise CreosonError(CREOSON_DOWN) from exc


def session_status(client, creo_version=None):
    """连接状态。Creo 没开时也返回结果，只有 CREOSON 没开才算失败。"""
    if creo_version is None:
        creo_version = creo_version_from_env()
    raw = connect_session(client)
    try:
        running = bool(raw.is_creo_running())
    except ConnectionError as exc:
        client.disconnect()
        raise CreosonError(CREOSON_DOWN) from exc

    active = None
    if running and not getattr(client, "_creo_version_sent", False):
        raw.creo_set_creo_version(int(creo_version))
        client._creo_version_sent = True
    if running:
        try:
            active = raw.file_get_active()
        except RuntimeError:
            # 没有打开任何模型时，CREOSON 可能返回错误。状态本身仍然有效。
            active = None
    return {
        "creoson": True,
        "host": client.host,
        "port": client.port,
        "creo_running": running,
        "creo_version": int(creo_version) if running else None,
        "active_model": active,
    }


def ensure_creo(client, creo_version=None):
    """多数建模工具都要 Creo 已经开着。"""
    status = session_status(client, creo_version=creo_version)
    if not status["creo_running"]:
        raise CreosonError(
            "CREOSON 已连上，但 Creo 没有打开。请先启动 Creo Parametric，或调用 start_creo。"
        )
    return client._require()


def start_creo(client, bat_path):
    """启动 Creo。文件名必须是 nitro_proe_remote.bat，这是 CREOSON 写死的限制。"""
    raw = connect_session(client)
    leaf = str(bat_path).replace("\\", "/").rstrip("/").split("/")[-1]
    if leaf.lower() != "nitro_proe_remote.bat":
        raise CreosonError(
            "启动文件的名字必须是 nitro_proe_remote.bat。这是 CREOSON 的规定。"
            "可以把 Creo 的 parametric.bat 复制一份，再改成这个名字。"
        )
    if bool(raw.is_creo_running()):
        return {
            "started": False,
            "creo_running": True,
            "message": "Creo 已经在运行，没有再次启动。",
        }
    # 文件名检查在客户端里：必须是 nitro_proe_remote.bat。
    client.start_creo(bat_path)
    return {"started": True, "creo_running": False, "bat_path": bat_path}


def working_directory(client):
    ensure_creo(client)
    return {"dirname": client.working_directory()}


def set_working_directory(client, dirname):
    ensure_creo(client)
    return {"dirname": client.set_working_directory(dirname)}


def list_workdir_files(client, filename=None):
    ensure_creo(client)
    return {"files": _as_list(client.list_workdir_files(filename=filename))}


def list_open_files(client):
    ensure_creo(client)
    return {"files": _as_list(client.list_open_files())}


def open_model(client, path):
    ensure_creo(client)
    opened = client.open_model(path)
    if isinstance(opened, dict):
        return opened
    return {"file": model_filename(path)}


def active_model(client):
    ensure_creo(client)
    return client.active_model() or {}


def list_parameters(client, name=None, file=None):
    ensure_creo(client)
    return {"parameters": _as_list(client.list_parameters(name=name, file_=file))}


def get_parameter(client, name, file=None):
    ensure_creo(client)
    rows = _as_list(client.list_parameters(name=name, file_=file))
    matched = [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("name", "")).lower() == name.lower()
    ]
    chosen = matched or rows
    if not chosen:
        raise CreosonError(
            f"模型里没有参数 {name}。请先在 Creo「工具 → 参数」里建立同名参数。"
        )
    if len(chosen) == 1:
        return {"parameter": chosen[0]}
    return {"parameters": chosen}


def set_parameter(client, name, value, file=None, type_name=None):
    """写入已有参数。模板里没有的参数不会新建。"""
    ensure_creo(client)
    stored, kind = coerce_parameter(value, type_name)
    client.set_parameter(name, stored, file_=file, type_=kind)
    return {"name": name, "value": _show(stored), "type": kind, "file": file}


def list_dimensions(client, name=None, file=None):
    ensure_creo(client)
    return {"dimensions": _as_list(client.list_dimensions(name=name, file_=file))}


def set_dimension(client, name, value, file=None):
    """直接改尺寸数值。若该尺寸由关系驱动，再生后会被参数盖回去。"""
    ensure_creo(client)
    number = float(value)
    client.set_dimension(name, number, file_=file)
    return {"name": name, "value": number, "file": file}


def regenerate(client, file=None):
    ensure_creo(client)
    client.regenerate(file_=file)
    return {"regenerated": True, "file": file}


def save_model(client, file=None, confirm_overwrite=False):
    """覆盖保存。必须显式确认，否则拒绝。"""
    ensure_creo(client)
    if confirm_overwrite is not True:
        raise CreosonError(
            "save_model 会覆盖磁盘上的同名文件。做变体请改用 save_as_copy。"
            "只有用户明确说要覆盖时，才把 confirm_overwrite 设为 true。"
        )
    client.save(file_=file)
    return {"saved": True, "file": file, "overwrote": True}


def save_as_copy(client, new_name, file=None, confirm_overwrite=False):
    """另存为新名字。默认若工作目录里已有同名文件就拒绝。"""
    ensure_creo(client)
    source = file or _active_name(client)
    target = normalize_copy_name(new_name, source)
    if confirm_overwrite is not True and _workdir_has(client, target):
        raise CreosonError(
            f"工作目录里已经有 {target}。请换一个名字，"
            "或在用户明确同意覆盖后把 confirm_overwrite 设为 true。"
        )
    saved = client.save_as_copy(target, file_=source)
    return {
        "saved_as": saved,
        "source": source,
        "note": "内存中的模型已改成新名字。原文件仍在磁盘上。下一步若还要改模板，请重新 open_model。",
    }


def export_model(client, kind, filename=None, dirname=None, file=None):
    """导出 STEP 或 PDF。STEP 用于零件，PDF 用于工程图。"""
    ensure_creo(client)
    kind_up = str(kind).strip().upper()
    if kind_up == "STEP":
        exported = client.export_step(file_=file, filename=filename, dirname=dirname)
    elif kind_up == "PDF":
        exported = client.export_pdf(file_=file, filename=filename, dirname=dirname)
    else:
        raise CreosonError("目前只导出 STEP 或 PDF。")
    if isinstance(exported, dict):
        return {"kind": kind_up, **exported}
    return {"kind": kind_up, "filename": filename, "dirname": dirname, "file": file}


def batch_from_csv(client, csv_path, template, confirm_overwrite=False):
    """按参数表逐行生成。每一行都重新打开模板，再另存为新文件。"""
    ensure_creo(client)
    table = load_parameter_table(csv_path)
    saved = []
    for row in table.rows:
        try:
            client.open_model(template)
            model_name = model_filename(template)
            for name, param in row.parameters.items():
                client.set_parameter(
                    name,
                    param.value,
                    file_=model_name,
                    type_=param.creo_type,
                )
            client.regenerate(file_=model_name)
            outcome = save_as_copy(
                client,
                row.output_filename,
                file=model_name,
                confirm_overwrite=confirm_overwrite,
            )
        except CreosonError as exc:
            raise CreosonError(f"处理 {row.output_filename} 时失败：{exc}") from exc
        except RuntimeError as exc:
            raise CreosonError(
                f"处理 {row.output_filename} 时，Creo 返回错误：{exc}"
            ) from exc
        saved.append(outcome["saved_as"])
    return {"template": template, "saved": saved, "count": len(saved)}


def coerce_parameter(value, type_name=None):
    """把智能体传来的值变成 Creo 参数值和类型名。"""
    if type_name:
        kind = str(type_name).strip().upper()
        if kind not in _PARAM_TYPES:
            raise CreosonError("type_name 只能是 STRING、DOUBLE、INTEGER、BOOL、NOTE。")
        if kind == "DOUBLE":
            return float(value), kind
        if kind == "INTEGER":
            return int(float(value)), kind
        if kind == "BOOL":
            if isinstance(value, bool):
                return value, kind
            parsed = parse_cell(str(value))
            if parsed.creo_type != "BOOL":
                raise CreosonError("BOOL 参数请传 true 或 false。")
            return parsed.value, kind
        return str(value), kind
    if isinstance(value, bool):
        return value, "BOOL"
    if isinstance(value, int):
        return value, "INTEGER"
    if isinstance(value, float):
        return value, "DOUBLE"
    parsed = parse_cell(str(value))
    return parsed.value, parsed.creo_type


def normalize_copy_name(new_name, source_name):
    """新文件只写文件名。缺扩展名时跟源文件走，零件默认 .prt。"""
    text = str(new_name).strip()
    if text == "":
        raise CreosonError("新文件名是空的。")
    if "/" in text or "\\" in text:
        raise CreosonError("新文件名不要带文件夹。例如 shaft_20x80.prt。")
    if not text.lower().endswith((".prt", ".asm", ".drw")):
        suffix = ".prt"
        if source_name and "." in str(source_name):
            suffix = str(source_name)[str(source_name).rfind(".") :]
        text = text + suffix
    if source_name and text.lower() == str(source_name).lower():
        raise CreosonError(
            "新文件名和当前模型相同。请换一个名字，避免覆盖模板。"
        )
    return text


def _active_name(client):
    active = client.active_model() or {}
    name = active.get("file") if isinstance(active, dict) else None
    if not name:
        raise CreosonError("当前没有活动模型。请先 open_model，或传入 file。")
    return name


def _workdir_has(client, filename):
    found = set()
    for item in _as_list(client.list_workdir_files()):
        text = str(item).replace("\\", "/").rstrip("/")
        found.add(text.lower())
        found.add(text.split("/")[-1].lower())
    return filename.lower() in found


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _show(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return value
