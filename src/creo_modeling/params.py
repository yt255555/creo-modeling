"""读取并检查参数表。

参数表是一个 CSV 文件：第一行是表头，下面每一行是一个零件。
必须有一列叫 variant，写零件名字。其余列的表头就是 Creo 里的参数名。

数字怎么区分类型（和 creopyson 的 type_ 一致）：
- 20.0、1.5 这种带小数点的数 → DOUBLE（实数，尺寸一般用这个）
- 4 这种不带小数点的数 → INTEGER（整数）
- true / false → BOOL（是 / 否）
- 其他文字 → STRING（字符串）
"""

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path


class ParamsError(Exception):
    """表格内容有问题。提示文字直接用中文。"""


# 零件名：字母开头，后面可以是字母、数字、下划线、减号，结尾可以带 .prt
_VARIANT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*(\.[Pp][Rr][Tt])?$")
# Creo 参数名：字母开头，后面只允许字母、数字、下划线
_PARAM_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_INTEGER = re.compile(r"[+-]?\d+")
_DOUBLE = re.compile(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?|[+-]?\d+[eE][+-]?\d+")

VARIANT_COLUMN = "variant"


# @dataclass 会自动生成“把下面几项数据装在一起”的代码，省得手写一堆 self.xxx = xxx。
@dataclass
class ParameterValue:
    """一个格子里的值，以及要传给 parameter_set 的类型名。"""

    value: object
    creo_type: str


@dataclass
class VariantRow:
    """表格中的一行。"""

    name: str
    parameters: dict
    line_number: int

    @property
    def output_filename(self):
        """计划生成的文件名。已经带 .prt 的就不再加。"""
        if self.name.lower().endswith(".prt"):
            return self.name
        return f"{self.name}.prt"


@dataclass
class ParameterTable:
    """整张表：参数列名（按表头顺序）和所有行。"""

    parameter_columns: list
    rows: list


def load_parameter_table(path):
    """从磁盘读取 CSV。认 UTF-8（含 Excel 的 UTF-8 带 BOM）和国标码 GB18030。"""
    file_path = Path(path)
    if not file_path.is_file():
        raise ParamsError(f"找不到文件：{file_path}")

    raw = file_path.read_bytes()
    if raw.strip() == b"":
        raise ParamsError(f"{file_path.name} 是空的。")

    text = _decode(raw, file_path.name)
    return parse_parameter_table(text, source_name=file_path.name)


def parse_parameter_table(text, source_name="参数表"):
    """检查表格文字并转成 ParameterTable。有问题就抛出 ParamsError。"""
    if text.strip() == "":
        raise ParamsError(f"{source_name} 是空的。")

    reader = csv.reader(io.StringIO(text))
    header_row = next(reader, None)
    if header_row is None:
        raise ParamsError(f"{source_name} 是空的。")

    header = [cell.strip() for cell in header_row]
    if not any(header):
        raise ParamsError("第一行是表头，不能是空的。请写上 variant 和参数名。")
    if any(name == "" for name in header):
        raise ParamsError("表头里有空的列名。请删掉空列，或给每一列起名字。")

    lowered = [name.lower() for name in header]
    if len(lowered) != len(set(lowered)):
        raise ParamsError("表头里有重复的列名。")
    if VARIANT_COLUMN not in lowered:
        raise ParamsError(
            "表头必须有一列叫 variant，用来写每个零件的名字。"
            "请用 Excel 的「CSV UTF-8（逗号分隔）」另存，不要用分号。"
        )

    variant_index = lowered.index(VARIANT_COLUMN)
    param_indexes = [i for i in range(len(header)) if i != variant_index]
    if not param_indexes:
        raise ParamsError("除了 variant，至少还要有一列参数，例如 D、L。")

    for index in param_indexes:
        _check_parameter_name(header[index])

    rows = []
    seen = {}
    for line_number, raw_row in enumerate(reader, start=2):
        # Excel 有时会在末尾留出完全空白的行，跳过即可。
        if not raw_row or all(cell.strip() == "" for cell in raw_row):
            continue
        extra = raw_row[len(header) :]
        if any(cell.strip() for cell in extra):
            raise ParamsError(f"第 {line_number} 行比表头多出了内容。")
        if len(raw_row) < len(header):
            raise ParamsError(
                f"第 {line_number} 行列数不够。表头有 {len(header)} 列。"
            )

        name = raw_row[variant_index].strip()
        if name == "":
            raise ParamsError(f"第 {line_number} 行的 variant 是空的。")
        if not _VARIANT_NAME.match(name):
            raise ParamsError(
                f"第 {line_number} 行的零件名「{name}」不合适。"
                "请用英文字母开头，只含字母、数字、下划线或减号，例如 shaft_20x80。"
            )
        key = name.lower()
        if key in seen:
            raise ParamsError(
                f"零件名「{name}」重复了（第 {seen[key]} 行和第 {line_number} 行）。"
            )
        seen[key] = line_number

        parameters = {}
        for index in param_indexes:
            column = header[index]
            cell = raw_row[index].strip()
            if cell == "":
                raise ParamsError(f"第 {line_number} 行的参数 {column} 是空的。")
            parameters[column] = parse_cell(cell)
        rows.append(
            VariantRow(name=name, parameters=parameters, line_number=line_number)
        )

    if not rows:
        raise ParamsError("表头下面没有数据。请至少写一行零件。")

    columns = [header[index] for index in param_indexes]
    return ParameterTable(parameter_columns=columns, rows=rows)


def parse_cell(text):
    """把一个格子变成值和 Creo 类型。"""
    lowered = text.lower()
    if lowered == "true":
        return ParameterValue(True, "BOOL")
    if lowered == "false":
        return ParameterValue(False, "BOOL")
    if _INTEGER.fullmatch(text):
        return ParameterValue(int(text), "INTEGER")
    if _DOUBLE.fullmatch(text):
        return ParameterValue(float(text), "DOUBLE")
    return ParameterValue(text, "STRING")


def _check_parameter_name(name):
    if not _PARAM_NAME.match(name):
        raise ParamsError(
            f"参数名「{name}」不合适。请用英文字母开头，"
            "只含字母、数字或下划线，并与 Creo 模型里的参数名一致。"
        )


def _decode(raw, display_name):
    # utf-8-sig 能同时读普通 UTF-8 和 Excel「CSV UTF-8」带的 BOM。
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ParamsError(
        f"无法识别 {display_name} 的编码。请用 Excel「CSV UTF-8（逗号分隔）」另存一次。"
    )
