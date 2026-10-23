# creo编程建模

这是一个给机械制图、Creo 教学用的小程序。

以后它可以读一张表格，让 Creo 按每一行的尺寸自动修改零件，一次做出很多相似的零件。比如一张表里有三行轴的直径和长度，程序就帮你生成三根轴。

**现在只是架子。** 读表格、检查表格、从命令行启动，这些已经能用。和 Creo 说话的函数也按真实的库写好了。把每个变体另存成单独的 `.prt` 还没做，所以请先用下面的「预演」来熟悉流程。

## 先把几个词说清楚

后面的步骤会反复用到这些词。看不懂时可以回到这里。

**Python**
一种编程语言。这个项目就是用 Python 写的。你现在不用学完它，只要把 Python 装到电脑上，再复制下面的命令运行即可。

**pip**
Python 自带的安装工具。别人写好的程序包（叫「库」）用 pip 下载安装。本项目要靠它安装一个叫 `creopyson` 的库。

**命令行**
一个用键盘打字来让电脑干活的窗口。Windows 里它常叫「命令提示符」，窗口一般是黑底白字。下面每一行以 `python` 开头的字，都是整行复制进去，再按回车。

**Creo**
PTC Creo Parametric，你上课用的三维 CAD 软件。

**参数**
Creo 模型里有名字的数或文字，例如直径 `D`。把尺寸用「关系」绑到参数上之后，改参数、再点「再生」，模型就变了。

**参数表**
一个 CSV 表格。第一行是表头，下面每一行是一个零件方案。CSV 就是用逗号分开的纯文本，Excel 可以打开，也可以另存成这种格式。

**模板零件**
你事先在 Creo 里建好的 `.prt`。程序打开它，再按表格去改参数。仓库里没有现成的 `.prt`，需要你自己做。做法写在 [examples/模板说明.md](examples/模板说明.md)。

**CREOSON**
一个开源的小服务器（[SimplifiedLogic/creoson](https://github.com/SimplifiedLogic/creoson)）。它运行着的时候，别的程序可以请 Creo 打开文件、改参数、再生、保存。你可以把它想成 Creo 旁边的一个传话窗口。默认端口是 `9056`。

**creopyson**
从 Python 给 CREOSON 传话的库。本项目把它包在 `src/creo_modeling/client.py` 里，名字和 [creopyson 文档](https://creopyson.readthedocs.io/en/latest/creopyson.html) 里的一致，例如 `connect`、`file_open`、`parameter_set`、`file_regenerate`、`file_save`。

**端口**
本机上一个编号，用来区分不同的服务。CREOSON 用 `9056`。程序和 CREOSON 约定好这个编号才能对上话。

## 现在能做什么，以后打算做什么

已经有的：

- 读取 CSV 参数表，并检查表头、空格、重复的零件名、参数名是否合法
- 命令 `validate`：只检查表格
- 命令 `batch --dry-run`：预演，打印每一行将要生成的文件名
- 命令 `batch`：连接 CREOSON，打开模板，按行写入参数并再生
- 一套不打开 Creo 也能通过的单元测试

还没做，按这个顺序往下加：

1. 每个变体另存为独立的 `.prt`，同时留下原来的模板。creopyson 没有单独的「另存为」，下一步会用文档里的 `file_backup` 或 `file_rename`
2. 某一行再生失败时记下原因，继续做下一行
3. 用 `start_creo` 启动 Creo（需要一个名为 `nitro_proe_remote.bat` 的启动文件）
4. 再加几张练习表，例如板、套筒
5. 如果命令行用顺了，再考虑做一个简单窗口

## 文件夹里都有什么

```
creo-modeling/
├── pyproject.toml            pip 读的项目配置
├── requirements.txt          运行需要的库（creopyson）
├── requirements-dev.txt      跑测试时额外需要的库
├── .gitignore                不放进 Git 的文件，含 Creo 的版本文件和轨迹
├── README.md                 本说明
├── src/creo_modeling/        程序本体
│   ├── cli.py                命令行：读你敲的命令
│   ├── params.py             读参数表、检查、区分整数/实数/文字
│   ├── client.py             连接 CREOSON 的薄封装，测试时可以换成假的
│   ├── batch.py              把表格和客户端串起来
│   ├── __main__.py           让 python -m creo_modeling 能启动
│   └── __init__.py
├── examples/
│   ├── shaft_variants.csv    三根轴的示例参数表
│   └── 模板说明.md           模板零件里要建哪些参数
└── tests/                    单元测试，不需要 Creo
```

建议以后读代码的顺序：`params.py` → `client.py` → `batch.py` → `cli.py`。文件里的注释是中文。

## 在 Windows 上从零开始

下面按顺序做。每一段代码都整行复制。请把路径换成你自己电脑上的真实位置。

### 1. 安装 Python

1. 用浏览器打开 <https://www.python.org/downloads/>
2. 下载 Python 3.12（或任何 3.9 以上的版本）
3. 运行安装程序。**第一页最下方勾选 “Add python.exe to PATH”**。这一项默认不勾。不勾的话，后面会提示找不到 `python`
4. 点击 “Install Now”，等到出现成功
5. 关掉安装程序。如果电脑里已经开着命令行窗口，也关掉，后面重新开一个

### 2. 打开命令行，确认 Python 和 pip 都能用

1. 按键盘上的 Windows 键，输入 `cmd`，打开「命令提示符」
2. 输入下面两行（每行输入完按回车）：

```bat
python --version
python -m pip --version
```

第一行应出现 `Python 3.12.x` 这样的字。第二行应出现带 `pip` 的一行字。

如果提示「python 不是内部或外部命令」，说明第 1 步的 PATH 没勾上。卸载 Python 后重装，并勾选那一项。如果弹出的是微软应用商店，关掉它，同样重装官方 Python。

### 3. 把本项目放到电脑上

初学最省事的办法是下载压缩包：

1. 打开 <https://github.com/yt255555/creo-modeling>
2. 点击绿色的 **Code**，再点 **Download ZIP**
3. 把压缩包解压到一个好找的文件夹，例如 `C:\Users\你的用户名\creo-modeling`
4. 在命令行里进入这个文件夹。`/d` 的意思是连盘符一起换：

```bat
cd /d C:\Users\你的用户名\creo-modeling
dir
```

`dir` 的结果里应能看到 `pyproject.toml` 和 `README.md`。路径以你解压的位置为准。路径里有空格时，整段路径加上英文引号。

如果你已经会用 Git，也可以：

```bat
git clone https://github.com/yt255555/creo-modeling.git
cd creo-modeling
```

### 4. 安装本项目

还是在上面的文件夹里，输入：

```bat
python -m pip install -e .
```

`-e` 表示「可编辑安装」：你以后改了这些 `.py` 文件，不用重新安装，命令就会用新代码。

这一步会同时安装 `creopyson`。学校网络如果下载很慢，改用国内镜像，整行是：

```bat
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

看到最后有 `Successfully installed` 就完成了。

### 5. 先检查示例表格，再做一次预演

这两步不需要打开 Creo，也不需要 CREOSON。用来确认项目已经装好。

检查表格：

```bat
python -m creo_modeling validate examples\shaft_variants.csv
```

预演批量生成（`--dry-run` 表示只打印计划，不去连 Creo）：

```bat
python -m creo_modeling batch examples\shaft_variants.csv --template shaft.prt --dry-run
```

成功时会看到三行，类似：

```text
共 3 个变体，参数列：D、L、C、MARK
- shaft_20x80.prt  D=20.0  L=80.0  C=1.0  MARK=A
- shaft_25x100.prt  D=25.0  L=100.0  C=1.5  MARK=B
- shaft_30x120.prt  D=30.0  L=120.0  C=2.0  MARK=C
```

这三行来自 [examples/shaft_variants.csv](examples/shaft_variants.csv)。

### 6. 确认 Creo 里有 J-Link

CREOSON 要通过 Creo 的 **J-Link** 才能控制软件。Creo 2.0 及以后可以，较新的版本里 J-Link 是安装时的可选项。

如果当初安装 Creo 时没有勾选 J-Link，用 Creo 的安装程序再跑一遍，补上 J-Link，不必重做模型。

### 7. 下载并启动 CREOSON

1. 打开 <https://github.com/SimplifiedLogic/creoson/releases>
2. 在最新版本里下载名字类似 `CreosonServerWithSetup-3.0.2-win64.zip` 的文件。数字可能更新，请选 **带 Setup、并且是 win64** 的那个压缩包
3. 解压到一个路径里尽量没有空格的文件夹，例如 `D:\creoson`
4. 双击里面的 `CreosonSetup.exe`
5. 选择你的 Creo 安装目录
6. 端口填 `9056`（这是 CREOSON 建议的默认端口）
7. 点击 **Start CREOSON**
8. 这个窗口要一直开着。关掉它，Creo 就收不到消息了
9. 如果 Windows 防火墙询问，允许它在专用网络上通信
10. 再自己打开 Creo。当前这个架子还不会自动启动 Creo

官方说明也写在 CREOSON 项目的首页：解压后运行 `CreosonSetup.exe`，选好 Creo 目录和端口，按 Start CREOSON。

### 8. 做一根模板轴

按 [examples/模板说明.md](examples/模板说明.md) 在 Creo 里做 `shaft.prt`。

模型里要有参数 `D`、`L`、`C`、`MARK`，并且用关系把直径、长度、倒角绑到 `D`、`L`、`C` 上。尺寸类参数在表格里写成带小数点的数，例如 `20.0`，程序会按实数交给 Creo。

做完后先在 Creo 里手动改一次参数并再生，确认模型会跟着变，再继续。

### 9. 真正跑一次 batch

把下面的路径换成你的 `shaft.prt`。路径有空格时，用英文引号包起来：

```bat
python -m creo_modeling batch examples\shaft_variants.csv --template D:\creo_work\shaft.prt
```

程序会连接本机 `9056` 端口的 CREOSON，打开模板，把三行参数依次写进去并再生。

当前版本到再生为止。它调用的是打开、改参数、再生，**还不会把三根轴存成三个新文件**，也不会主动调用保存。Creo 会话里的模板数值会被改成最后一行。重要的模板请先「文件 → 保存副本」留一份，做完后先不要把改过的模型保存覆盖原文件。

只想换端口或地址时，可以加上：

```bat
python -m creo_modeling batch examples\shaft_variants.csv --template D:\creo_work\shaft.prt --host localhost --port 9056
```

## 这几条命令分别在说什么

以预演那条为例：

```bat
python -m creo_modeling batch examples\shaft_variants.csv --template shaft.prt --dry-run
```

- `python`：启动 Python
- `-m creo_modeling`：运行本项目（`-m` 表示按模块运行）
- `batch`：子命令，按表格处理零件
- `examples\shaft_variants.csv`：参数表的位置
- `--template shaft.prt`：模板零件。`--template` 是选项的名字，后面紧跟文件
- `--dry-run`：预演。有这个词就只打印计划

`validate` 把 `batch` 换成检查表格，不需要 `--template`。

在 Creo 的当前工作目录里能找到零件时，`--template` 只写文件名 `shaft.prt` 即可。零件在别的文件夹时，写完整路径。程序会把路径拆开，文件名和文件夹分别传给 creopyson 的 `file_open`。

## 想确认程序本身没坏（可选）

测试是写好的自动检查。它们用一个假的 CREOSON 客户端，所以没有 Creo 也能跑。

```bat
python -m pip install -r requirements-dev.txt
python -m pytest
```

学校网络慢时，同样可以在命令末尾加上 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。

最后一行出现 `passed` 就表示这些检查通过了。

## 遇到这些问题时

**命令行里中文变成乱码**

先输入下面这一行，再重新运行程序。它把窗口的文字编码改成 UTF-8：

```bat
chcp 65001
```

**提示找不到 variant 列**

表格需要用英文逗号分隔。在 Excel 里选择「另存为」→「CSV UTF-8（逗号分隔）(*.csv)」。用「CSV（逗号分隔）」以外的格式，或用分号时，程序会读不到表头。

**提示连不上 CREOSON**

确认 `CreosonSetup` 里已经按了 Start CREOSON，黑色的运行窗口还在，端口是 `9056`。然后确认 Creo 已经打开。

**改了参数但模型形状没变**

回到 Creo 检查「工具 → 关系」里，尺寸符号是不是写成了 `d0 = D` 这种形式，并已经再生成功过一次。参数名字要和表格表头一致。

## 程序现在停在哪里

`batch` 在 `src/creo_modeling/batch.py` 里，对每一行会：

1. `parameter_set` 写入这一行的参数（模板里没有的参数不会新建）
2. `file_regenerate` 再生

接着应把模型另存为这一行的文件名，例如 `shaft_20x80.prt`。这一步在代码里标了 `TODO`，所以现在不会调用 `file_save`。`client.py` 里的 `save()` 已经按文档接好了 `file_save`，等另存为的做法确定后才会用到它。
