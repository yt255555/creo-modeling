"""把参数表和 CREOSON 客户端串起来。

目前做到：连接、打开模板、按每一行写入参数、再生。
另存为独立的 .prt 还没做。这里故意不调用 save()，避免把模板覆盖掉。
"""

from creo_modeling.client import model_filename


def run_batch(client, table, template, dry_run=False):
    """按表格处理模板。

    dry_run 为真时只返回计划文件名，不连接 Creo。
    返回值是每个变体计划使用的文件名，例如 shaft_20x80.prt。
    """
    planned = [row.output_filename for row in table.rows]
    if dry_run:
        return planned

    model_name = model_filename(template)
    client.connect()
    try:
        client.open_model(template)
        for row in table.rows:
            for name, param in row.parameters.items():
                client.set_parameter(
                    name,
                    param.value,
                    file_=model_name,
                    type_=param.creo_type,
                )
            client.regenerate(model_name)
            # 命令行这条路径仍然不保存，避免上课时覆盖模板。
            # 另存为新零件在 MCP 工具 batch_from_csv 里：内存改名后再 file_save。
    finally:
        # 无论中间是否出错，都尝试断开，免得占着会话。
        client.disconnect()
    return planned
