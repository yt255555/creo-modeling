"""检查建模工具的安全规则。用假的 creopyson，不打开 Creo。"""

from unittest.mock import MagicMock

import pytest

from creo_modeling.client import CreosonClient, CreosonError
from creo_modeling.tools import (
    CREOSON_DOWN,
    batch_from_csv,
    export_model,
    save_as_copy,
    save_model,
    session_status,
    set_parameter,
    start_creo,
)


def _ready():
    client = CreosonClient(host="localhost", port=9056)
    raw = MagicMock()
    client._client = raw
    raw.is_creo_running.return_value = True
    raw.file_get_active.return_value = {"file": "shaft.prt", "dirname": r"D:\lab"}
    raw.creo_list_files.return_value = ["shaft.prt"]
    raw.file_rename.return_value = "shaft_20x80.prt"
    raw.file_open.return_value = {"files": ["shaft.prt"], "dirname": r"D:\lab"}
    return client, raw


def test_session_status_when_creoson_is_down():
    client = CreosonClient()
    client.connect = MagicMock(side_effect=ConnectionError("refused"))
    with pytest.raises(CreosonError, match="9056") as caught:
        session_status(client)
    assert "CREOSON" in str(caught.value)
    assert CREOSON_DOWN in str(caught.value)


def test_session_status_reports_creo_stopped_without_setting_version():
    client, raw = _ready()
    raw.is_creo_running.return_value = False
    status = session_status(client, creo_version=12)
    assert status["creoson"] is True
    assert status["creo_running"] is False
    assert status["port"] == 9056
    raw.creo_set_creo_version.assert_not_called()


def test_session_status_sends_creo_12_once():
    client, raw = _ready()
    first = session_status(client, creo_version=12)
    second = session_status(client, creo_version=12)
    assert first["creo_running"] is True
    assert first["creo_version"] == 12
    assert second["active_model"]["file"] == "shaft.prt"
    raw.creo_set_creo_version.assert_called_once_with(12)


def test_save_model_refuses_without_explicit_overwrite():
    client, raw = _ready()
    with pytest.raises(CreosonError, match="confirm_overwrite"):
        save_model(client, file="shaft.prt", confirm_overwrite=False)
    raw.file_save.assert_not_called()


def test_save_model_overwrites_only_when_confirmed():
    client, raw = _ready()
    result = save_model(client, file="shaft.prt", confirm_overwrite=True)
    assert result["overwrote"] is True
    raw.file_save.assert_called_once_with(file_="shaft.prt")


def test_save_as_copy_keeps_a_new_name():
    client, raw = _ready()
    result = save_as_copy(client, "shaft_20x80", file="shaft.prt")
    assert result["saved_as"] == "shaft_20x80.prt"
    raw.file_rename.assert_called_once_with(
        "shaft_20x80.prt", file_="shaft.prt", onlysession=True
    )
    raw.file_save.assert_called_once_with(file_="shaft_20x80.prt")


def test_save_as_copy_refuses_the_template_name_and_existing_files():
    client, raw = _ready()
    with pytest.raises(CreosonError, match="相同"):
        save_as_copy(client, "shaft.prt", file="shaft.prt")
    raw.creo_list_files.return_value = ["shaft_20x80.prt"]
    with pytest.raises(CreosonError, match="已经有"):
        save_as_copy(client, "shaft_20x80.prt", file="shaft.prt")
    raw.file_rename.assert_not_called()


def test_export_only_step_and_pdf():
    client, raw = _ready()
    export_model(client, "step", filename="shaft.stp", file="shaft.prt")
    export_model(client, "PDF", filename="shaft.pdf", file="shaft.drw")
    raw.interface_export_file.assert_called_once()
    assert raw.interface_export_file.call_args.args[0] == "STEP"
    raw.interface_export_pdf.assert_called_once()
    with pytest.raises(CreosonError, match="STEP"):
        export_model(client, "IGES")


def test_set_parameter_sends_a_double_for_decimals():
    client, raw = _ready()
    set_parameter(client, "D", "20.0", file="shaft.prt")
    raw.parameter_set.assert_called_once_with(
        "D",
        value=20.0,
        file_="shaft.prt",
        type_="DOUBLE",
        no_create=True,
    )


def test_start_creo_skips_a_second_launch_and_rejects_other_bat_names():
    client, raw = _ready()
    running = start_creo(client, r"C:\CREOSON\nitro_proe_remote.bat")
    assert running["started"] is False
    raw.start_creo.assert_not_called()

    raw.is_creo_running.return_value = False
    with pytest.raises(CreosonError, match="nitro_proe_remote.bat"):
        start_creo(client, r"C:\CREOSON\start.bat")
    raw.is_creo_running.return_value = False
    started = start_creo(client, r"C:\CREOSON\nitro_proe_remote.bat")
    assert started["started"] is True
    raw.start_creo.assert_called_once_with(r"C:\CREOSON\nitro_proe_remote.bat")


def test_batch_reopens_template_and_saves_each_row(tmp_path):
    csv_path = tmp_path / "shaft.csv"
    csv_path.write_text("variant,D\nshaft_a,20.0\nshaft_b,25.0\n", encoding="utf-8")
    client, raw = _ready()
    raw.file_rename.side_effect = ["shaft_a.prt", "shaft_b.prt"]
    result = batch_from_csv(client, str(csv_path), r"D:\lab\shaft.prt")
    assert result["saved"] == ["shaft_a.prt", "shaft_b.prt"]
    assert raw.file_open.call_count == 2
    assert raw.file_regenerate.call_count == 2
    assert raw.file_save.call_args_list[0].kwargs["file_"] == "shaft_a.prt"
    assert raw.file_save.call_args_list[1].kwargs["file_"] == "shaft_b.prt"
    assert all(call.kwargs.get("onlysession") is True for call in raw.file_rename.call_args_list)
