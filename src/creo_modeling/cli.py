"""命令行入口。

两个子命令：
- validate  只检查参数表，不连接 Creo
- batch     按参数表处理模板。加上 --dry-run 则只预演
"""

import argparse

from creo_modeling.batch import run_batch
from creo_modeling.client import CreosonClient, CreosonError
from creo_modeling.params import ParamsError, load_parameter_table


def main(argv=None):
    """解析命令并执行。返回 0 表示成功，其他数字表示失败。"""
    parser = argparse.ArgumentParser(
        prog="creo_modeling",
        description="用参数表批量生成 Creo 零件。当前是框架，另存为新零件还没做。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="只检查参数表，不连接 Creo")
    validate.add_argument("csv_path", help="参数表 CSV 的路径")

    batch = sub.add_parser("batch", help="按参数表打开模板并写入参数")
    batch.add_argument("csv_path", help="参数表 CSV 的路径")
    batch.add_argument(
        "--template",
        required=True,
        help="模板零件，例如 shaft.prt，也可以写完整路径",
    )
    batch.add_argument(
        "--host",
        default="localhost",
        help="CREOSON 所在地址，默认 localhost（本机）",
    )
    batch.add_argument(
        "--port",
        type=int,
        default=9056,
        help="CREOSON 端口，默认 9056",
    )
    batch.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要生成的零件，不连接 Creo",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return _validate(args.csv_path)
        return _batch(args)
    except ParamsError as exc:
        print(f"参数表有问题：{exc}")
        return 1
    except CreosonError as exc:
        print(f"CREOSON 出错：{exc}")
        return 1
    except ConnectionError as exc:
        print("连不上 CREOSON。")
        print("请确认 CreosonSetup 里已经按下 Start CREOSON，端口是 9056，窗口还开着。")
        print(f"详细信息：{exc}")
        return 1
    except RuntimeError as exc:
        # creopyson 在 CREOSON 返回错误时抛出 RuntimeError，消息来自服务器。
        print("Creo 或 CREOSON 返回了错误：")
        print(exc)
        return 1


def _validate(csv_path):
    table = load_parameter_table(csv_path)
    _print_table(table)
    print("参数表检查通过。")
    return 0


def _batch(args):
    table = load_parameter_table(args.csv_path)
    if args.dry_run:
        names = run_batch(None, table, args.template, dry_run=True)
        print("这是预演，没有连接 Creo。")
        _print_table(table)
        print("计划中的文件：" + "、".join(names))
        print("去掉 --dry-run 才会真的连接 CREOSON。当前版本仍不会另存为新零件。")
        return 0

    print(f"正在连接 CREOSON（{args.host}:{args.port}）。")
    print("将打开模板、写入参数并再生。当前版本不会保存，也不会另存为新文件。")
    print("如果这份模板很重要，请先在 Creo 里复制一份再试。")
    client = CreosonClient(host=args.host, port=args.port)
    names = run_batch(client, table, args.template, dry_run=False)
    print("已按表格写入参数并再生。")
    print("这些变体还没有存成独立文件：" + "、".join(names))
    print("另存为新零件仍是待做步骤。请先不要在 Creo 里把改过的模型保存覆盖模板。")
    return 0


def _print_table(table):
    columns = "、".join(table.parameter_columns)
    print(f"共 {len(table.rows)} 个变体，参数列：{columns}")
    for row in table.rows:
        pieces = []
        for name, param in row.parameters.items():
            pieces.append(f"{name}={_show(param.value)}")
        detail = "  ".join(pieces)
        print(f"- {row.output_filename}  {detail}")


def _show(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
