"""MCP 工具列表和调用。客户端是假的，不连接 CREOSON。"""

import asyncio
import json
from unittest.mock import MagicMock

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from creo_modeling.client import CreosonClient
from creo_modeling.mcp_server import build_server

EXPECTED_TOOLS = {
    "session_status",
    "start_creo",
    "working_directory",
    "set_working_directory",
    "list_workdir_files",
    "list_open_files",
    "open_model",
    "active_model",
    "list_parameters",
    "get_parameter",
    "set_parameter",
    "list_dimensions",
    "set_dimension",
    "regenerate",
    "save_model",
    "save_as_copy",
    "export_model",
    "batch_from_csv",
}


def _server():
    client = CreosonClient(host="127.0.0.1", port=9056)
    raw = MagicMock()
    client._client = raw
    raw.is_creo_running.return_value = True
    raw.file_get_active.return_value = {"file": "shaft.prt", "dirname": r"D:\lab"}
    raw.creo_list_files.return_value = []
    raw.file_open.return_value = {"files": ["shaft.prt"], "dirname": r"D:\lab"}
    raw.file_rename.return_value = "shaft_20x80.prt"
    server = build_server(client)
    return server, raw


def test_server_lists_the_safe_tool_set():
    server, _raw = _server()
    tools = asyncio.run(server.list_tools())
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == EXPECTED_TOOLS
    blocked = {"erase", "delete", "file_erase", "creo_delete_files"}
    assert blocked.isdisjoint(by_name)
    assert by_name["save_model"].annotations.destructive_hint is True
    assert by_name["list_parameters"].annotations.read_only_hint is True
    overwrite = by_name["save_model"].input_schema["properties"]["confirm_overwrite"]
    assert overwrite["default"] is False


def test_session_status_tool_explains_a_dead_creoson():
    client = CreosonClient()
    client.connect = MagicMock(side_effect=ConnectionError("refused"))
    server = build_server(client)
    with pytest.raises(ToolError, match="CREOSON"):
        asyncio.run(server.call_tool("session_status", {}))


def test_open_model_tool_returns_json():
    server, raw = _server()
    result = asyncio.run(server.call_tool("open_model", {"path": r"D:\lab\shaft.prt"}))
    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["files"] == ["shaft.prt"]
    raw.file_open.assert_called_once_with(
        "shaft.prt",
        dirname=r"D:\lab",
        display=True,
        activate=True,
    )


def test_save_model_tool_requires_confirm_overwrite():
    server, raw = _server()
    with pytest.raises(ToolError, match="confirm_overwrite"):
        asyncio.run(server.call_tool("save_model", {"file": "shaft.prt"}))
    raw.file_save.assert_not_called()
