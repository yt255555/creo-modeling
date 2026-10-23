"""检查批量流程是否按顺序调用客户端，并且还不保存。"""

import pytest

from creo_modeling.batch import run_batch
from creo_modeling.client import CreosonError
from creo_modeling.params import parse_parameter_table

TABLE = parse_parameter_table(
    "variant,D,L\nshaft_a,20.0,80.0\nshaft_b,25.0,100.0\n"
)


class FakeClient:
    """记下被调用的方法，形状和 CreosonClient 一样。"""

    def __init__(self):
        self.calls = []

    def connect(self):
        self.calls.append("connect")

    def disconnect(self):
        self.calls.append("disconnect")

    def open_model(self, template):
        self.calls.append(("open", template))

    def set_parameter(self, name, value, file_=None, type_=None):
        self.calls.append(("set", name, value, file_, type_))

    def regenerate(self, file_=None):
        self.calls.append(("regen", file_))

    def save(self, file_=None):
        self.calls.append(("save", file_))


def test_dry_run_does_not_touch_the_client():
    client = FakeClient()
    names = run_batch(client, TABLE, "shaft.prt", dry_run=True)
    assert names == ["shaft_a.prt", "shaft_b.prt"]
    assert client.calls == []


def test_batch_sets_parameters_then_regenerates():
    client = FakeClient()
    names = run_batch(client, TABLE, r"D:\lab\shaft.prt")

    assert names == ["shaft_a.prt", "shaft_b.prt"]
    assert client.calls[0] == "connect"
    assert client.calls[1] == ("open", r"D:\lab\shaft.prt")
    assert ("set", "D", 20.0, "shaft.prt", "DOUBLE") in client.calls
    assert ("set", "L", 100.0, "shaft.prt", "DOUBLE") in client.calls
    assert client.calls.count(("regen", "shaft.prt")) == 2
    assert client.calls[-1] == "disconnect"
    assert all(call[0] != "save" for call in client.calls if isinstance(call, tuple))
    assert "save" not in client.calls


def test_disconnects_when_open_fails():
    class Boom(FakeClient):
        def open_model(self, template):
            raise CreosonError("打不开")

    client = Boom()
    with pytest.raises(CreosonError, match="打不开"):
        run_batch(client, TABLE, "shaft.prt")
    assert client.calls == ["connect", "disconnect"]
