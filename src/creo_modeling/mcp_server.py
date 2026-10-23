"""MCP 服务器：让别的 AI 通过标准输入输出操作 Creo。

官方 Python 包名是 mcp。2.x 里原来的 FastMCP 改名为 MCPServer，
装饰器仍然是 @mcp.tool()，传输方式用 stdio。智能体启动的命令是：

    python -m creo_modeling.mcp_server

工具说明用英文，因为读这些说明的是 AI。报错用中文，方便老师在对话里看懂。
stdout 是 MCP 的通道，这里不要 print。
"""

import os
import sys
from functools import wraps

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from creo_modeling.client import CreosonClient, CreosonError
from creo_modeling import tools as creo_tools

_READ = ToolAnnotations(read_only_hint=True, destructive_hint=False)
_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False)
_OVERWRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    title="Overwrite the open Creo file",
)


def build_server(client=None):
    """组装服务器。测试可以传入一个假的客户端。"""
    if client is None:
        client = CreosonClient(
            host=os.environ.get("CREOSON_HOST", "localhost"),
            port=_port_from_env(),
        )

    mcp = MCPServer(
        "creo-modeling",
        instructions=(
            "Drive PTC Creo Parametric through CREOSON on this Windows PC. "
            "Call session_status first. If Creo is not running, ask the user "
            "to open it. Edit parameters, regenerate, then save_as_copy under "
            "a new file name. save_model overwrites the open file and requires "
            "confirm_overwrite=true. Never erase or delete models."
        ),
    )

    @mcp.tool(annotations=_READ)
    @_guard
    def session_status() -> dict:
        """Check CREOSON and whether Creo is running.

        Returns creoson, host, port, creo_running, creo_version, and active_model.
        Fails with a clear message when the CREOSON server is not started.
        """
        return creo_tools.session_status(client)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def start_creo(bat_path: str) -> dict:
        """Start Creo via CREOSON.

        bat_path must be the full path of a file named nitro_proe_remote.bat.
        CREOSON rejects every other file name. If Creo is already running, this
        does not start a second session.
        """
        return creo_tools.start_creo(client, bat_path)

    @mcp.tool(annotations=_READ)
    @_guard
    def working_directory() -> dict:
        """Return Creo's current working directory."""
        return creo_tools.working_directory(client)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def set_working_directory(dirname: str) -> dict:
        """Change Creo's working directory. dirname may be absolute or relative."""
        return creo_tools.set_working_directory(client, dirname)

    @mcp.tool(annotations=_READ)
    @_guard
    def list_workdir_files(filename: str | None = None) -> dict:
        """List files in Creo's working directory (on disk, not only open models).

        filename is an optional wildcard filter such as *.prt.
        """
        return creo_tools.list_workdir_files(client, filename=filename)

    @mcp.tool(annotations=_READ)
    @_guard
    def list_open_files() -> dict:
        """List models currently open in the Creo session."""
        return creo_tools.list_open_files(client)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def open_model(path: str) -> dict:
        """Open a model from a file name or a full Windows path and activate it."""
        return creo_tools.open_model(client, path)

    @mcp.tool(annotations=_READ)
    @_guard
    def active_model() -> dict:
        """Return the active model's file name and directory."""
        return creo_tools.active_model(client)

    @mcp.tool(annotations=_READ)
    @_guard
    def list_parameters(name: str | None = None, file: str | None = None) -> dict:
        """List parameters on a model. Omit name to list all of them."""
        return creo_tools.list_parameters(client, name=name, file=file)

    @mcp.tool(annotations=_READ)
    @_guard
    def get_parameter(name: str, file: str | None = None) -> dict:
        """Get one named parameter. The parameter must already exist on the model."""
        return creo_tools.get_parameter(client, name, file=file)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def set_parameter(
        name: str,
        value: str | int | float | bool,
        file: str | None = None,
        type_name: str | None = None,
    ) -> dict:
        """Set an existing parameter. Does not create a missing parameter.

        Dimensions should be decimals (20.0 or "20.0") so they are sent as DOUBLE.
        A whole number is sent as INTEGER. true/false is BOOL. Other text is STRING.
        type_name may be STRING, DOUBLE, INTEGER, BOOL, or NOTE.
        """
        return creo_tools.set_parameter(
            client, name, value, file=file, type_name=type_name
        )

    @mcp.tool(annotations=_READ)
    @_guard
    def list_dimensions(name: str | None = None, file: str | None = None) -> dict:
        """List dimension symbols and values. Does not change the Creo selection."""
        return creo_tools.list_dimensions(client, name=name, file=file)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def set_dimension(name: str, value: float, file: str | None = None) -> dict:
        """Set a dimension value by its symbol, such as d0.

        If a relation drives that dimension, regenerate will restore the relation.
        Prefer set_parameter for template variants.
        """
        return creo_tools.set_dimension(client, name, value, file=file)

    @mcp.tool(annotations=_WRITE)
    @_guard
    def regenerate(file: str | None = None) -> dict:
        """Regenerate the model so geometry matches the new parameters."""
        return creo_tools.regenerate(client, file=file)

    @mcp.tool(annotations=_OVERWRITE)
    @_guard
    def save_model(file: str | None = None, confirm_overwrite: bool = False) -> dict:
        """Overwrite the model file on disk.

        Refuses unless confirm_overwrite is true. Use save_as_copy for a variant.
        """
        return creo_tools.save_model(
            client, file=file, confirm_overwrite=confirm_overwrite
        )

    @mcp.tool(annotations=_WRITE)
    @_guard
    def save_as_copy(
        new_name: str,
        file: str | None = None,
        confirm_overwrite: bool = False,
    ) -> dict:
        """Save the active model under a new file name and keep the original on disk.

        new_name is a file name, not a path. After this call the in-session model
        uses the new name; open the template again before editing another variant.
        Refuses when that file name is already in the working directory unless
        confirm_overwrite is true.
        """
        return creo_tools.save_as_copy(
            client,
            new_name,
            file=file,
            confirm_overwrite=confirm_overwrite,
        )

    @mcp.tool(annotations=_WRITE)
    @_guard
    def export_model(
        kind: str,
        filename: str | None = None,
        dirname: str | None = None,
        file: str | None = None,
    ) -> dict:
        """Export the model. kind is STEP (parts) or PDF (drawings)."""
        return creo_tools.export_model(
            client,
            kind,
            filename=filename,
            dirname=dirname,
            file=file,
        )

    @mcp.tool(annotations=_WRITE)
    @_guard
    def batch_from_csv(
        csv_path: str,
        template: str,
        confirm_overwrite: bool = False,
    ) -> dict:
        """Build one variant per CSV row: open template, set parameters, regenerate, save_as_copy.

        The template file on disk is kept. Each output name comes from the variant column.
        confirm_overwrite must be true to replace an existing output file.
        """
        return creo_tools.batch_from_csv(
            client,
            csv_path,
            template,
            confirm_overwrite=confirm_overwrite,
        )

    return mcp


def _guard(func):
    """把连接失败和 Creo 的报错收成一句 ToolError，避免只甩出一长串英文堆栈。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ToolError:
            raise
        except CreosonError as exc:
            raise ToolError(str(exc)) from exc
        except ConnectionError as exc:
            raise ToolError(creo_tools.CREOSON_DOWN) from exc
        except RuntimeError as exc:
            raise ToolError(f"Creo 或 CREOSON 返回了错误：{exc}") from exc

    return wrapper


def _port_from_env():
    raw = os.environ.get("CREOSON_PORT", "9056")
    try:
        return int(raw)
    except ValueError:
        print("CREOSON_PORT 必须是整数，例如 9056。", file=sys.stderr)
        raise SystemExit(1)


def main():
    """给 `python -m creo_modeling.mcp_server` 用。阻塞，直到智能体断开。"""
    server = build_server()
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
