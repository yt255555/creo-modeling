"""检查 CREOSON 封装有没有叫对 creopyson 的函数。用假的 creopyson，不连接服务器。"""

import sys
from unittest.mock import MagicMock

import pytest

from creo_modeling.client import CreosonClient, CreosonError, split_creo_path


def _connect(monkeypatch, host="localhost", port=9056):
    """往 sys.modules 里放一个假的 creopyson，再连接。"""
    fake_module = MagicMock()
    raw = MagicMock()
    fake_module.Client.return_value = raw
    monkeypatch.setitem(sys.modules, "creopyson", fake_module)
    client = CreosonClient(host=host, port=port)
    client.connect()
    return client, fake_module, raw


def test_connect_uses_creopyson_argument_names(monkeypatch):
    """库的参数名是 ip_adress（少一个 d），端口默认 9056。"""
    _client, fake_module, raw = _connect(monkeypatch, host="127.0.0.1", port=9056)
    fake_module.Client.assert_called_once_with(ip_adress="127.0.0.1", port=9056)
    raw.connect.assert_called_once_with()


def test_open_plain_filename(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.open_model("shaft.prt")
    raw.file_open.assert_called_once_with(
        "shaft.prt",
        dirname=None,
        display=True,
        activate=True,
    )


def test_open_windows_path(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.open_model(r"D:\lab\shaft.prt")
    raw.file_open.assert_called_once_with(
        "shaft.prt",
        dirname=r"D:\lab",
        display=True,
        activate=True,
    )


def test_split_relative_folder():
    assert split_creo_path("models/shaft.prt") == ("shaft.prt", "models")
    assert split_creo_path("shaft.prt") == ("shaft.prt", None)


def test_set_parameter_does_not_create_missing(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.set_parameter("D", 20.0, file_="shaft.prt", type_="DOUBLE")
    raw.parameter_set.assert_called_once_with(
        "D",
        value=20.0,
        file_="shaft.prt",
        type_="DOUBLE",
        no_create=True,
    )


def test_regenerate_and_save(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.regenerate("shaft.prt")
    client.save("shaft.prt")
    raw.file_regenerate.assert_called_once_with(file_="shaft.prt", display=False)
    raw.file_save.assert_called_once_with(file_="shaft.prt")


def test_disconnect_is_safe_twice(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.disconnect()
    client.disconnect()
    raw.disconnect.assert_called_once_with()


def test_call_before_connect_fails():
    client = CreosonClient()
    with pytest.raises(CreosonError, match="还没有连接"):
        client.open_model("shaft.prt")


def test_list_and_parameter_calls(monkeypatch):
    """这些名字对照已安装的 creopyson 0.7.8。"""
    client, _fake_module, raw = _connect(monkeypatch)
    client.working_directory()
    client.set_working_directory(r"D:\lab")
    client.list_workdir_files("*.prt")
    client.list_open_files()
    client.list_parameters(name="D", file_="shaft.prt")
    client.list_dimensions(file_="shaft.prt")
    client.set_dimension("d0", 20.0, file_="shaft.prt")
    client.set_creo_version(12)
    raw.creo_pwd.assert_called_once_with()
    raw.creo_cd.assert_called_once_with(r"D:\lab")
    raw.creo_list_files.assert_called_once_with(filename="*.prt")
    raw.file_list.assert_called_once_with(file_=None)
    raw.parameter_list.assert_called_once_with(name="D", file_="shaft.prt")
    raw.dimension_list.assert_called_once_with(
        name=None, file_="shaft.prt", select=False
    )
    raw.dimension_set.assert_called_once_with("d0", 20.0, file_="shaft.prt")
    raw.creo_set_creo_version.assert_called_once_with(12)


def test_save_as_copy_renames_in_session_then_saves(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    raw.file_rename.return_value = "shaft_20x80.prt"
    saved = client.save_as_copy("shaft_20x80.prt", file_="shaft.prt")
    assert saved == "shaft_20x80.prt"
    raw.file_rename.assert_called_once_with(
        "shaft_20x80.prt", file_="shaft.prt", onlysession=True
    )
    raw.file_save.assert_called_once_with(file_="shaft_20x80.prt")


def test_export_step_and_pdf(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    client.export_step(file_="shaft.prt", filename="shaft.stp", dirname=r"D:\out")
    client.export_pdf(file_="shaft.drw", filename="shaft.pdf")
    raw.interface_export_file.assert_called_once_with(
        "STEP",
        file_="shaft.prt",
        filename="shaft.stp",
        dirname=r"D:\out",
        geom_flags="solids",
    )
    raw.interface_export_pdf.assert_called_once_with(
        file_="shaft.drw",
        filename="shaft.pdf",
        dirname=None,
    )


def test_start_creo_requires_the_creoson_bat_name(monkeypatch):
    client, _fake_module, raw = _connect(monkeypatch)
    with pytest.raises(CreosonError, match="nitro_proe_remote.bat"):
        client.start_creo(r"C:\CREOSON\parametric.bat")
    raw.start_creo.assert_not_called()
    client.start_creo(r"C:\CREOSON\nitro_proe_remote.bat")
    raw.start_creo.assert_called_once_with(r"C:\CREOSON\nitro_proe_remote.bat")
