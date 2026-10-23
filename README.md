# creo编程建模

这是一个给机械制图老师用的小程序，也是给别的 AI 用的 Creo 插件。

AI（Cursor、Claude、Codex 这类）自己不会去点 Creo 的菜单。本项目在你的 Windows 电脑上开一个小服务，AI 通过它请 Creo 打开模板、改参数、再生，再另存成新零件。中间传话的是 CREOSON。这台电脑上的环境是 Creo Parametric 12.4.4.0、CREOSON 3.0.2（放在 `C:\CREOSON`，端口 `9056`）、Python 3.12。

你也可以先不接 AI，只用命令行检查表格、做预演。命令行里的 `batch` 停在再生，不会把变体存成新文件。真正另存为新名字的是后面的 MCP 工具。

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

**MCP**
一种让 AI 调用外部工具的插头标准，全称 Model Context Protocol。你可以把它想成：AI 是客人，MCP 是插座，本项目是插在插座上的 Creo 遥控器。遥控器跑在你自己的电脑上，零件文件不用上传到网上。详细接法在后面的「让 AI 操作 Creo」。

## 现在能做什么，以后打算做什么

已经有的：

- 读取 CSV 参数表，并检查表头、空格、重复的零件名、参数名是否合法
- 命令 `validate`：只检查表格
- 命令 `batch --dry-run`：预演，打印每一行将要生成的文件名
- 命令 `batch`：连接 CREOSON，打开模板，按行写入参数并再生（命令行这一条仍不保存）
- MCP 服务：连接状态、工作目录、打开模型、读写参数和尺寸、再生、另存为新名字、导出 STEP/PDF、按 CSV 批量另存
- 一套不打开 Creo 也能通过的单元测试
- `SKILL.md`：教 AI 按安全步骤使用这些工具

还没做：

1. 某一行再生失败时记下原因，继续做下一行
2. 命令行 `batch` 也改成和 MCP 一样另存为新文件
3. 再加几张现成的法兰、轴套练习表（用法已经写在 `SKILL.md`）

## 文件夹里都有什么

```
creo-modeling/
├── pyproject.toml            pip 读的项目配置
├── requirements.txt          运行需要的库（creopyson）
├── requirements-dev.txt      跑测试时额外需要的库
├── .gitignore                不放进 Git 的文件，含 Creo 的版本文件和轨迹
├── README.md                 本说明（给人看）
├── SKILL.md                  教 AI 怎么安全地操作 Creo
├── AGENTS.md                 教 Codex / Claude 怎么改这个项目
├── CLAUDE.md                 指向 AGENTS.md 的短说明
├── src/creo_modeling/        程序本体
│   ├── cli.py                命令行：读你敲的命令
│   ├── params.py             读参数表、检查、区分整数/实数/文字
│   ├── client.py             连接 CREOSON 的薄封装，测试时可以换成假的
│   ├── tools.py              MCP 用的操作，以及哪些动作不允许
│   ├── mcp_server.py         给 AI 用的 MCP 服务
│   ├── batch.py              命令行批量流程（再生，不保存）
│   ├── __main__.py           让 python -m creo_modeling 能启动
│   └── __init__.py
├── examples/
│   ├── shaft_variants.csv    三根轴的示例参数表
│   └── 模板说明.md           模板零件里要建哪些参数
└── tests/                    单元测试，不需要 Creo
```

建议以后读代码的顺序：`params.py` → `client.py` → `tools.py` → `mcp_server.py` → `batch.py` → `cli.py`。给人看的注释是中文。MCP 工具的说明是英文，因为读它的是 AI。

## 在 Windows 上从零开始

下面按顺序做。每一段代码都整行复制。请把路径换成你自己电脑上的真实位置。

### 1. 安装 Python

1. 用浏览器打开 <https://www.python.org/downloads/>
2. 下载 Python 3.12（或任何 3.10 以上的版本。本机用的是 3.12）
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

这一步会同时安装 `creopyson`（跟 CREOSON 说话）和 `mcp`（跟 AI 说话）。学校网络如果下载很慢，改用国内镜像，整行是：

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

### 6. 确认 Creo 里有 Object TOOLKIT Java and J-Link

CREOSON 要通过 Creo 的 **Object TOOLKIT Java and J-Link** 才能控制软件。这个安装项会带上 `pfcasync.jar`。没装这一项时，CREOSON 连不上模型。

如果当初安装 Creo 12.4.4.0 时没有勾选它，再运行一次 Creo 的安装程序，选择修改安装，勾上 **Object TOOLKIT Java and J-Link**。模型不用重做。装完后在 Creo 安装目录里搜索 `pfcasync.jar`，能找到就说明这一项在。安装目录通常类似 `C:\Program Files\PTC\Creo 12.4.4.0\`。

### 7. 下载并启动 CREOSON

1. 打开 <https://github.com/SimplifiedLogic/creoson/releases>
2. 在最新版本里下载名字类似 `CreosonServerWithSetup-3.0.2-win64.zip` 的文件。数字可能更新，请选 **带 Setup、并且是 win64** 的那个压缩包
3. 解压到一个路径里尽量没有空格的文件夹。这台电脑用的是 `C:\CREOSON`
4. 双击里面的 `CreosonSetup.exe`
5. 选择你的 Creo 安装目录
6. 端口填 `9056`（这是 CREOSON 建议的默认端口）
7. 点击 **Start CREOSON**
8. 这个窗口要一直开着。关掉它，Creo 就收不到消息了
9. 如果 Windows 防火墙询问，允许它在专用网络上通信
10. 再自己打开 Creo Parametric 12。也可以以后让 AI 调用 `start_creo`，但启动文件必须叫 `nitro_proe_remote.bat`

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

## 让 AI 操作 Creo（MCP）

MCP 是 AI 和外部程序之间的一种插头。客人是 Cursor、Claude Desktop、Claude Code 或 Codex。插座上的遥控器是本项目。遥控器通过命令行的「标准输入 / 标准输出」和 AI 说话（这种方式叫 stdio），再由 creopyson 把请求交给本机 `9056` 端口的 CREOSON，CREOSON 再交给 Creo。

零件留在你的电脑上。AI 只收到工具返回的文字，例如「已打开 shaft.prt」。

先做完上面的安装，并确认这两件事：

1. `C:\CREOSON` 里的 CreosonSetup 已经按下 Start CREOSON，窗口还开着，端口是 `9056`
2. Creo Parametric 12 已经打开

然后在项目文件夹里试一次服务器本身。输入：

```bat
python -m creo_modeling.mcp_server
```

窗口会停住，看起来像没反应。这是正常的：它在等 AI 从标准输入发来消息。看到没有报错后，按 `Ctrl+C` 结束。如果提示找不到模块，回到项目文件夹再执行一次 `python -m pip install -e .`。

如果某个软件提示找不到 `python`，把下面配置里的 `python` 换成安装程序放好的完整路径，例如：

```text
C:\Users\你的用户名\AppData\Local\Programs\Python\Python312\python.exe
```

在资源管理器地址栏输入 `%LocalAppData%\Programs\Python` 可以找到它。路径里的反斜杠，在 JSON 里要写成 `\\`，在 TOML 的单引号字符串里保持一条 `\`。

接好以后，在 AI 的对话里说：「先看 Creo 的连接状态。」它应该调用 `session_status`。让它改模型之前，把 [SKILL.md](SKILL.md) 指给它，里面写了安全步骤（先查连接、再改参数、再生、另存为新名字，不覆盖模板）。

### Cursor

项目里新建文件 `.cursor/mcp.json`（全局则是 `C:\Users\你的用户名\.cursor\mcp.json`）。格式来自 Cursor 文档：[cursor.com/docs/mcp](https://cursor.com/docs/mcp)。本地服务要写 `type`、`command`、`args`。

```json
{
  "mcpServers": {
    "creo-modeling": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "creo_modeling.mcp_server"],
      "env": {
        "CREOSON_HOST": "localhost",
        "CREOSON_PORT": "9056",
        "CREO_VERSION": "12"
      }
    }
  }
}
```

保存后重载窗口，或关掉 Cursor 再打开。在 Settings → MCP 里应能看到 `creo-modeling`。

### Claude Desktop

配置文件在：

```text
C:\Users\你的用户名\AppData\Roaming\Claude\claude_desktop_config.json
```

也可以从 Claude Desktop 的 Settings → Developer → Edit Config 打开。本地服务用 `command`、`args`、`env`。改完后完全退出 Claude Desktop 再打开。

```json
{
  "mcpServers": {
    "creo-modeling": {
      "command": "python",
      "args": ["-m", "creo_modeling.mcp_server"],
      "env": {
        "CREOSON_HOST": "localhost",
        "CREOSON_PORT": "9056",
        "CREO_VERSION": "12"
      }
    }
  }
}
```

文件里如果已经有别的 `mcpServers`，只把 `creo-modeling` 这一段加进现有的大括号，不要再套一层。

### Claude Code

在已经装好 Claude Code 的命令行里执行。选项写在名字前面，`--` 后面才是启动服务器的命令。这是 [Claude Code MCP 文档](https://code.claude.com/docs/en/mcp) 里的写法：`--env` 不要紧挨着服务器名字，中间放 `--transport stdio`，否则名字会被当成另一个环境变量。

`--scope user` 表示这台电脑上的各个项目都能用。Creo 装在这台机器上，用用户范围合适。

```bat
claude mcp add --scope user --env CREOSON_HOST=localhost --env CREOSON_PORT=9056 --env CREO_VERSION=12 --transport stdio creo-modeling -- python -m creo_modeling.mcp_server
```

成功时会打印一行 `Added stdio MCP server creo-modeling ...`。然后执行：

```bat
claude mcp get creo-modeling
```

新开一个 Claude Code 会话后再让它查连接状态。

### Codex CLI

Codex 把 MCP 写在 `C:\Users\你的用户名\.codex\config.toml`。ChatGPT 桌面版、Codex CLI 和 IDE 插件共用这一份。格式来自 [Codex MCP 文档](https://learn.chatgpt.com/docs/extend/mcp.md?surface=cli)：`[mcp_servers.名字]` 里要有 `command`，参数放在 `args`，环境变量单独放一张 `env` 表。

可以直接贴进 `config.toml`：

```toml
[mcp_servers.creo-modeling]
command = "python"
args = ["-m", "creo_modeling.mcp_server"]

[mcp_servers.creo-modeling.env]
CREOSON_HOST = "localhost"
CREOSON_PORT = "9056"
CREO_VERSION = "12"
```

`python` 不在 Codex 能看见的路径里时，把 `command` 换成单引号包住的完整路径（单引号里反斜杠不用加倍）：

```toml
command = 'C:\Users\你的用户名\AppData\Local\Programs\Python\Python312\python.exe'
```

也可以让 Codex 自己写入同一份配置。`--` 后面是启动命令：

```bat
codex mcp add creo-modeling --env CREOSON_HOST=localhost --env CREOSON_PORT=9056 --env CREO_VERSION=12 -- python -m creo_modeling.mcp_server
```

在 Codex 里输入 `/mcp` 可以查看已连接的服务。

### 其他使用 stdio 的客户端

凡是用「一条命令 + 标准输入输出」接 MCP 的软件，都用同一组启动参数：

```json
{
  "command": "python",
  "args": ["-m", "creo_modeling.mcp_server"],
  "env": {
    "CREOSON_HOST": "localhost",
    "CREOSON_PORT": "9056",
    "CREO_VERSION": "12"
  }
}
```

外层的键名随软件而变。Cursor、Claude Desktop、Claude Code 用 `mcpServers`。Codex 用上面的 TOML。

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

## 两条批量路径

命令行 `batch`（`src/creo_modeling/batch.py`）对每一行写入参数并再生，然后停住，不调用保存。上课时先用 `--dry-run` 或这一条，模板文件不会被写成新名字。

MCP 工具 `batch_from_csv` 和 `save_as_copy` 会另存。creopyson 没有单独的「另存为」，做法是文档里的两步：`file_rename` 且 `onlysession` 为真（只改内存中的名字），再 `file_save` 把新名字写入磁盘。原来的模板文件还在。另存之后，会话里的当前模型已经换成新名字，下一件变体要重新打开模板。

`save_model` 会覆盖同名文件，必须传入 `confirm_overwrite: true` 才会执行。没有提供擦除会话或删除文件的工具。
