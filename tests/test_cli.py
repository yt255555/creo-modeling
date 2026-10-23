"""从命令行走一遍。预演和检查都不连接 Creo。"""

from pathlib import Path

from creo_modeling.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "shaft_variants.csv"


def test_validate_example(capsys):
    code = main(["validate", str(EXAMPLE)])
    text = capsys.readouterr().out
    assert code == 0
    assert "shaft_30x120.prt" in text
    assert "检查通过" in text


def test_validate_missing_file(capsys, tmp_path):
    code = main(["validate", str(tmp_path / "no.csv")])
    text = capsys.readouterr().out
    assert code == 1
    assert "找不到文件" in text


def test_dry_run_prints_plan_without_client(monkeypatch, capsys):
    def explode(*_args, **_kwargs):
        raise AssertionError("预演不应该去连接 CREOSON")

    monkeypatch.setattr("creo_modeling.cli.CreosonClient", explode)
    code = main(
        ["batch", str(EXAMPLE), "--template", "shaft.prt", "--dry-run"]
    )
    text = capsys.readouterr().out
    assert code == 0
    assert "预演" in text
    assert "shaft_20x80.prt" in text


def test_batch_constructs_client_and_does_not_save(monkeypatch, capsys, tmp_path):
    csv_path = tmp_path / "one.csv"
    csv_path.write_text("variant,D\nshaft_a,20.0\n", encoding="utf-8")
    holder = {}

    class FakeClient:
        def __init__(self, host="localhost", port=9056):
            holder["host"] = host
            holder["port"] = port
            holder["calls"] = []

        def connect(self):
            holder["calls"].append("connect")

        def disconnect(self):
            holder["calls"].append("disconnect")

        def open_model(self, template):
            holder["calls"].append(("open", template))

        def set_parameter(self, name, value, file_=None, type_=None):
            holder["calls"].append(("set", name, value, type_))

        def regenerate(self, file_=None):
            holder["calls"].append(("regen", file_))

        def save(self, file_=None):
            holder["calls"].append("save")

    monkeypatch.setattr("creo_modeling.cli.CreosonClient", FakeClient)
    code = main(
        [
            "batch",
            str(csv_path),
            "--template",
            r"D:\lab\shaft.prt",
            "--host",
            "127.0.0.1",
            "--port",
            "9056",
        ]
    )
    assert code == 0
    assert holder["host"] == "127.0.0.1"
    assert holder["port"] == 9056
    assert holder["calls"][0] == "connect"
    assert ("set", "D", 20.0, "DOUBLE") in holder["calls"]
    assert ("regen", "shaft.prt") in holder["calls"]
    assert "save" not in holder["calls"]
    assert "另存为" in capsys.readouterr().out
