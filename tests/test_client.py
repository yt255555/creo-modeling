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
