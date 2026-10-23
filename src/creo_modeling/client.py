"""和 CREOSON 通信的薄封装。

真正发请求的是第三方库 creopyson（0.7.8）。这里只包一层，
测试时可以用一个假的客户端换掉它，这样就不必打开 Creo。

下面这些名字对照官方文档，没有猜测：
https://creopyson.readthedocs.io/en/latest/creopyson.html

已封装：
- creopyson.Client(ip_adress=..., port=9056) 然后 connect() / disconnect()
- file_open(file_, dirname=None, display=..., activate=...)
- parameter_set(name, value=..., file_=..., type_=..., no_create=...)
- file_regenerate(file_=..., display=...)
- file_save(file_=...)

以后再接（现在不要调用，避免误改模型）：
- is_creo_running()
- start_creo(path)  启动文件必须叫 nitro_proe_remote.bat
- file_backup(target_dir, file_=...)  把模型复制到另一个文件夹
- file_rename(new_name, file_=..., onlysession=...)
"""

from pathlib import Path


class CreosonError(Exception):
    """连不上 CREOSON，或者还没连接就调用了别的函数。"""


def split_creo_path(template):
    """把路径拆成 CREOSON 要的「文件名」和「所在文件夹」。

    file_open 不收整段路径。`D:\\lab\\shaft.prt` 要拆成
    文件名 shaft.prt、文件夹 D:\\lab。只有文件名时，文件夹留空，
    Creo 就用它自己的当前工作目录。
    """
    text = template.strip().strip('"')
    if text == "":
        raise CreosonError("模板路径是空的。")

    # Windows 用反斜杠。这里先换成正斜杠，方便 pathlib 在任何系统上拆开。
    uses_backslash = "\\" in text
    path = Path(text.replace("\\", "/"))
    filename = path.name
    if filename in ("", ".", ".."):
        raise CreosonError(f"看不懂的模板路径：{template}")

    parent = path.parent
    if str(parent) in ("", "."):
        return filename, None

    dirname = str(parent)
    if uses_backslash:
        dirname = dirname.replace("/", "\\")
    return filename, dirname


def model_filename(template):
    """会话里的模型名就是文件名，不含文件夹。"""
    filename, _dirname = split_creo_path(template)
    return filename


class CreosonClient:
    """持有一个 creopyson.Client。没调用 connect() 之前，其他方法都会拒绝。"""

    def __init__(self, host="localhost", port=9056):
        self.host = host
        self.port = port
        # _client 是 creopyson 的对象。前面加下划线，表示外面别直接碰它。
        self._client = None

    def connect(self):
        """连接本机的 CREOSON。默认地址 localhost，端口 9056。"""
        # 放在函数里面导入：单元测试可以先塞一个假的 creopyson，不必真的安装。
        import creopyson

        # 参数名是 ip_adress，少了一个 d。这是 creopyson 源码里的拼写，不能改成 address。
        self._client = creopyson.Client(ip_adress=self.host, port=self.port)
        self._client.connect()

    def disconnect(self):
        """断开连接。还没连接时再调用也没关系。"""
        if self._client is None:
            return
        self._client.disconnect()
        self._client = None

    def _require(self):
        if self._client is None:
            raise CreosonError("还没有连接 CREOSON。请先调用 connect()。")
        return self._client

    def open_model(self, template):
        """打开模板零件。template 可以是 shaft.prt，也可以是完整路径。"""
        client = self._require()
        filename, dirname = split_creo_path(template)
        # display=True 让零件显示出来；activate=True 让它成为当前模型。
        return client.file_open(
            filename,
            dirname=dirname,
            display=True,
            activate=True,
        )

    def set_parameter(self, name, value, file_=None, type_=None):
        """修改一个参数。

        type_ 用 creopyson 规定的大写名字：STRING、DOUBLE、INTEGER、BOOL。
        no_create=True：模板里没有这个参数时不要偷偷新建。
        """
        client = self._require()
        client.parameter_set(
            name,
            value=value,
            file_=file_,
            type_=type_,
            no_create=True,
        )

    def regenerate(self, file_=None):
        """再生模型，让尺寸按新参数重算。

        CREOSON 若返回错误，creopyson 会抛出 RuntimeError。
        """
        client = self._require()
        client.file_regenerate(file_=file_, display=False)

    def save(self, file_=None):
        """保存当前模型（file_save）。

        这会写回打开的那个文件。批量生成时如果直接保存，会覆盖模板。
        在想好「另存为」之前，batch 流程不要调用本方法。
        """
        client = self._require()
        client.file_save(file_=file_)
