"""和 CREOSON 通信的薄封装。

真正发请求的是第三方库 creopyson（0.7.8）。这里只包一层，
测试时可以用一个假的客户端换掉它，这样就不必打开 Creo。

下面这些名字对照官方文档，没有猜测：
https://creopyson.readthedocs.io/en/latest/creopyson.html

已封装（名字对照 creopyson 0.7.8，没有猜测）：
- creopyson.Client(ip_adress=..., port=9056)、connect()、disconnect()、is_creo_running()
- start_creo(path)  启动文件必须叫 nitro_proe_remote.bat
- creo_pwd()、creo_cd(dirname)、creo_list_files(filename=None)、creo_set_creo_version(version)
- file_open、file_list（当前会话里打开的文件）、file_get_active
- parameter_list、parameter_set（no_create=True）
- dimension_list（select=False）、dimension_set(name, value, file_=...)
- file_regenerate、file_save
- file_rename(..., onlysession=True) 再 file_save：另存为新名字，原文件留在磁盘上
- interface_export_file("STEP", ...) 与 interface_export_pdf(...)

不封装会删文件的函数：file_erase、file_erase_not_displayed、creo_delete_files、creo_rmdir。
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
        # 连接成功以后才记下对象。失败时 _client 仍是空的，避免半连接。
        raw = creopyson.Client(ip_adress=self.host, port=self.port)
        raw.connect()
        self._client = raw

    def disconnect(self):
        """断开连接。还没连接时再调用也没关系。"""
        # 下次重新连上后，要再告诉 CREOSON 一次 Creo 版本。
        self._creo_version_sent = False
        raw = self._client
        self._client = None
        if raw is None:
            return
        try:
            raw.disconnect()
        except ConnectionError:
            # 服务器已经关掉时，断开请求也会失败。这时连接本来就已经没了。
            return

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
        """保存当前模型（file_save）。会覆盖磁盘上的同名文件。"""
        client = self._require()
        client.file_save(file_=file_)

    def is_creo_running(self):
        """问 CREOSON：Creo 现在是否开着。必须先 connect()。"""
        return self._require().is_creo_running()

    def set_creo_version(self, version):
        """告诉 CREOSON 当前是哪一版 Creo。Creo 7 及以后，再生前需要这一步。

        creopyson 0.7.8 的说明文字还写着只支持 7、8、9，函数本身只把整数发出去。
        本机是 Creo 12，由调用方传入 12。
        """
        self._require().creo_set_creo_version(int(version))

    def start_creo(self, bat_path):
        """用 CREOSON 启动 Creo。bat_path 的文件名必须是 nitro_proe_remote.bat。"""
        leaf = str(bat_path).replace("\\", "/").rstrip("/").split("/")[-1]
        if leaf.lower() != "nitro_proe_remote.bat":
            raise CreosonError(
                "启动文件的名字必须是 nitro_proe_remote.bat。这是 CREOSON 的规定。"
            )
        self._require().start_creo(bat_path)

    def working_directory(self):
        """Creo 当前工作目录（creo_pwd）。"""
        return self._require().creo_pwd()

    def set_working_directory(self, dirname):
        """切换 Creo 工作目录（creo_cd）。返回新的目录。"""
        return self._require().creo_cd(dirname)

    def list_workdir_files(self, filename=None):
        """列出工作目录里的文件（creo_list_files），不是内存里打开的模型。"""
        return self._require().creo_list_files(filename=filename)

    def list_open_files(self, file_=None):
        """列出当前 Creo 会话里打开的模型（file_list）。"""
        return self._require().file_list(file_=file_)

    def active_model(self):
        """当前活动模型。返回值含 file 和 dirname。"""
        return self._require().file_get_active()

    def list_parameters(self, name=None, file_=None):
        """列出参数（parameter_list）。name 为空时列出全部。"""
        return self._require().parameter_list(name=name, file_=file_)

    def list_dimensions(self, name=None, file_=None):
        """列出尺寸（dimension_list）。select=False，不去改动 Creo 里的选择。"""
        return self._require().dimension_list(name=name, file_=file_, select=False)

    def set_dimension(self, name, value, file_=None):
        """修改一个尺寸的数值（dimension_set）。参数顺序是名字、数值、文件。"""
        self._require().dimension_set(name, value, file_=file_)

    def save_as_copy(self, new_name, file_=None):
        """另存为新文件名，磁盘上的原文件保留。

        creopyson 没有 save_as。按文档分两步：
        1. file_rename(new_name, onlysession=True) 只改内存中的名字
        2. file_save(新名字) 把改名后的模型写到磁盘
        """
        raw = self._require()
        renamed = raw.file_rename(new_name, file_=file_, onlysession=True)
        target = renamed if isinstance(renamed, str) and renamed else new_name
        raw.file_save(file_=target)
        return target

    def export_step(self, file_=None, filename=None, dirname=None):
        """导出 STEP（interface_export_file，类型 STEP，几何为 solids）。"""
        return self._require().interface_export_file(
            "STEP",
            file_=file_,
            filename=filename,
            dirname=dirname,
            geom_flags="solids",
        )

    def export_pdf(self, file_=None, filename=None, dirname=None):
        """导出 PDF（interface_export_pdf）。工程图用这个；零件更适合 STEP。"""
        return self._require().interface_export_pdf(
            file_=file_,
            filename=filename,
            dirname=dirname,
        )
