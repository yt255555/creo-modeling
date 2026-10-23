"""检查参数表的测试。不打开 Creo。"""

from pathlib import Path

import pytest

from creo_modeling.params import (
    ParamsError,
    load_parameter_table,
    parse_cell,
    parse_parameter_table,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "shaft_variants.csv"


def test_example_shaft_table():
    """示例 CSV 里有三根轴，尺寸是实数，记号是文字。"""
    table = load_parameter_table(EXAMPLE)

    assert table.parameter_columns == ["D", "L", "C", "MARK"]
    assert len(table.rows) == 3
    assert table.rows[0].name == "shaft_20x80"
    assert table.rows[0].output_filename == "shaft_20x80.prt"
    assert table.rows[1].output_filename == "shaft_25x100.prt"

    diameter = table.rows[0].parameters["D"]
    assert type(diameter.value) is float
    assert diameter.value == 20.0
    assert diameter.creo_type == "DOUBLE"

    chamfer = table.rows[1].parameters["C"]
    assert chamfer.value == 1.5
    assert chamfer.creo_type == "DOUBLE"

    mark = table.rows[0].parameters["MARK"]
    assert mark.value == "A"
    assert mark.creo_type == "STRING"


def test_integer_bool_and_existing_prt_suffix():
    text = "variant,COUNT,FLAG\nshaft_a.prt,4,true\n"
    table = parse_parameter_table(text)

    assert table.rows[0].output_filename == "shaft_a.prt"
    count = table.rows[0].parameters["COUNT"]
    assert type(count.value) is int
    assert count.value == 4
    assert count.creo_type == "INTEGER"
    flag = table.rows[0].parameters["FLAG"]
    assert flag.value is True
    assert flag.creo_type == "BOOL"


def test_false_ignores_case():
    assert parse_cell("FALSE").value is False
    assert parse_cell("FALSE").creo_type == "BOOL"


def test_utf8_bom_and_blank_lines(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes("variant,D\n\nshaft_a,20.0\n\n".encode("utf-8-sig"))
    table = load_parameter_table(path)
    assert table.rows[0].name == "shaft_a"


def test_gb18030_chinese_text(tmp_path):
    """国内 Excel 有时会存成国标码，这种情况也要能读。"""
    path = tmp_path / "gb.csv"
    path.write_bytes("variant,MARK\nshaft_a,轴\n".encode("gb18030"))
    table = load_parameter_table(path)
    assert table.rows[0].parameters["MARK"].value == "轴"


def test_missing_file(tmp_path):
    with pytest.raises(ParamsError, match="找不到文件"):
        load_parameter_table(tmp_path / "missing.csv")


def test_missing_variant_column():
    with pytest.raises(ParamsError, match="variant"):
        parse_parameter_table("D,L\n20.0,80.0\n")


def test_duplicate_variant_name():
    text = "variant,D\nshaft_a,20.0\nShaft_A,21.0\n"
    with pytest.raises(ParamsError, match="重复"):
        parse_parameter_table(text)


def test_empty_cell_reports_line_number():
    text = "variant,D\nshaft_a,\n"
    with pytest.raises(ParamsError, match="第 2 行"):
        parse_parameter_table(text)


def test_bad_parameter_name():
    with pytest.raises(ParamsError, match="直径"):
        parse_parameter_table("variant,直径\nshaft_a,20.0\n")


def test_header_only():
    with pytest.raises(ParamsError, match="没有数据"):
        parse_parameter_table("variant,D\n")
