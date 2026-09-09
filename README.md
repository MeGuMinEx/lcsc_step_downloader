# JLC STEP Downloader

按立创商城编号下载 STEP 三维模型，保留源文件中的颜色定义。支持 Windows 独立 exe、Bash 和 Python 命令行，原来的网页下载方式也可继续使用。

例如 `C41427486`：普通 EasyEDA 元件接口查不到时，工具会自动使用商城交互式 3D 预览的封装查询接口。

## Windows exe

构建后的程序位于 `dist/jlc-downloader.exe`，可以单独复制到其他目录使用，无需安装 Python。

在 PowerShell 中运行：

```powershell
.\dist\jlc-downloader.exe --ID C41427486
.\dist\jlc-downloader.exe --ID C41427486 C2040 -o .\models
.\dist\jlc-downloader.exe "https://www.lcsc.com/product-detail/C41427486.html" -o .\models
```

默认输出到**运行命令时所在的目录**，文件名为 `C41427486.step`，与 exe 所在目录无关。
将 `dist` 目录加入用户 PATH 并重新打开终端后，在任意目录运行：

```powershell
jlc-downloader --ID C41427486
```

不提供 `-o` 就下载到当前目录；提供 `-o` 才使用指定目录。`--id` 小写形式和原来的 `jlc-downloader C41427486` 用法也继续支持。

## Bash / Python 命令

需要 Python 3.10 或更新版本。在仓库目录安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
jlc-downloader --ID C41427486 C2040 -o ./models
```

也可以使用仓库中的 Bash 启动脚本：

```bash
bash ./jlc-downloader --ID C41427486 -o ./models
```

它优先使用 Windows 构建产物或项目的虚拟环境，并保留调用者的工作目录。Git Bash 也支持这个入口。

Windows 的 Python 安装方式：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\jlc-downloader.exe C41427486 -o .\models
```

通过 Python 模块调用的等价形式为 `python -m jlc_downloader C41427486`。

## 参数和脚本调用

| 参数 | 作用 |
| --- | --- |
| `--ID LCSC_ID ...` / `--id LCSC_ID ...` | 指定一个或多个编号，也可以重复使用此参数 |
| `LCSC_ID ...` | 一个或多个编号；支持含编号的 LCSC 商品链接、立创搜索链接 |
| `-o DIR` / `--output-dir DIR` | 输出目录，默认当前目录 |
| `--overwrite` | 覆盖已存在的文件；默认跳过 |
| `--timeout SECONDS` | 每个网络请求的超时，默认 30 秒 |
| `--json` | 向标准输出写入一个 JSON 对象 |
| `--verbose` | 向标准错误输出诊断日志 |
| `--version` / `--help` | 查看版本或帮助 |

批量下载遇到某个器件失败时，会继续处理其他器件。重复编号只处理一次。
输出文件先写入临时文件，成功后再保存为最终文件，避免留下不完整的 STEP。

```bash
jlc-downloader C41427486 C2040 -o ./models --json > result.json
```

JSON 的顶层字段为 `ok` 和 `results`。每项包含 `lcsc_id`、`status`，成功时还包含 `path`、`name`、`uuid`、`bytes`、`source`；失败时包含 `error`。`status` 为 `downloaded`、`skipped` 或 `error`。

退出码：`0` 全部成功或跳过，`1` 下载/写入失败，`2` 参数错误，`130` 用户中断。参数错误通过标准错误输出 argparse 帮助信息。网络请求支持 Requests 标准的 `HTTPS_PROXY` 等环境变量。

## 原网页方式

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[web]"
.\.venv\Scripts\python.exe downloader.py
```

打开 http://127.0.0.1:5000，输入编号下载。直接下载地址为 `/get_model/C41427486`。网页和命令行共用相同的下载逻辑。

## 构建和验证

在 Windows 中构建单文件 exe，同时生成 Python wheel 和源码包：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web]" -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

产物输出到 `dist/`。exe 内嵌 Python、运行依赖和许可证文件。构建需要 Windows；Python 包和 Bash 入口可以在 Linux/macOS 使用。运行时仍需联网访问 EasyEDA/LCSC。

工具只读取预览所需的封装名称和 3D UUID，再下载源 STEP，不转换模型、不重新着色。CLI 运行依赖只有 Requests，不需要 Flask 或 easyeda2kicad。即使网页有 3D 预览，服务器仍需提供对应 STEP 文件才能下载。

## 项目来源

基于 [wormyrocks/lcsc_step_downloader](https://github.com/wormyrocks/lcsc_step_downloader) 的 MIT 项目扩展，保留原版权声明。当前仓库为 [MeGuMinEx/lcsc_step_downloader](https://github.com/MeGuMinEx/lcsc_step_downloader)。

软件许可证见 [LICENSE](LICENSE)，运行依赖说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
