鸣谢：本项目参考并基于 [wormyrocks 的 lcsc_step_downloader](https://github.com/wormyrocks/lcsc_step_downloader) 修改而来。感谢原作者提供的项目，原始版权声明保留在 [LICENSE](LICENSE) 中。

# JLC STEP Downloader

按立创商城编号下载 STEP 三维模型，保留源文件中的颜色定义。提供两个版本：

- **Python 版**：安装依赖后，直接运行 `jlc-downloader.py`，也可调用 Python 函数。
- **Windows exe 版**：内置 Python 和依赖，下载即可运行。

两种版本默认把 `C41427486.step` 保存到**运行命令时的当前目录**，与程序所在目录无关。

## 下载

前往 [GitHub Releases](https://github.com/MeGuMinEx/lcsc_step_downloader/releases/latest)，下载所需版本：

| 文件 | 用途 |
| --- | --- |
| [jlc-downloader.exe](https://github.com/MeGuMinEx/lcsc_step_downloader/releases/latest/download/jlc-downloader.exe) | Windows x64 独立程序，自带运行库 |
| [jlc-downloader-python.zip](https://github.com/MeGuMinEx/lcsc_step_downloader/releases/latest/download/jlc-downloader-python.zip) | Python 源码包，解压后自行安装依赖 |

## exe 版使用方式

无需另行安装 Python 或 easyeda2kicad。在 exe 所在目录打开 PowerShell：

```powershell
.\jlc-downloader.exe --ID C41427486
```

如需在任意目录直接调用，把 **exe 所在文件夹**手动加入 PATH，重新打开终端后运行：

```powershell
jlc-downloader --ID C41427486
```

```powershell
# 批量下载到当前目录
jlc-downloader --ID C41427486 C2040

# 下载到指定目录
jlc-downloader --ID C41427486 -o .\models

# 覆盖已有文件
jlc-downloader --ID C41427486 --overwrite
```

Git Bash 中可运行 `./jlc-downloader.exe --ID C41427486`；加入 PATH 后同样可以直接运行 `jlc-downloader`。

## Python 版使用方式

需要 Python 3.10 或更新版本。下载并解压 Python 源码包，进入包含 `jlc-downloader.py` 的目录，直接安装依赖：

```bash
python -m pip install easyeda2kicad==1.0.1 requests
```

也可以执行 `python -m pip install -r requirements.txt`。

运行：

```bash
python jlc-downloader.py --ID C41427486
python jlc-downloader.py --ID C41427486 C2040 -o ./models
```

如果本机 Python 命令为 `python3`，把示例中的 `python` 换成 `python3`。请保留源码包内的 `jlc_downloader` 文件夹，它与入口脚本配套使用。

## Python 运行函数

在源码目录下，或将项目安装到当前 Python 环境后，调用 `download_model(...)`：

```python
from jlc_downloader import download_model

# 下载到当前工作目录，返回文件的绝对路径（pathlib.Path）
path = download_model("C41427486")
print(path)

# 指定输出目录和可选参数
path = download_model(
    "C2040",
    output_dir="./models",
    overwrite=True,
    timeout=30,
)
print(path)
```

`output_dir` 默认当前目录，`overwrite` 默认 `False`，`timeout` 默认每个请求 30 秒。已有文件会保留并返回其路径；设置 `overwrite=True` 才重新下载。网络或模型查询失败抛出 `jlc_downloader.DownloadError`，文件写入失败抛出 `OSError`。

## 参数

| 参数 | 作用 |
| --- | --- |
| `--ID LCSC_ID ...` / `--id LCSC_ID ...` | 一个或多个编号 |
| `LCSC_ID ...` | 也支持直接传入编号，或包含编号的商城链接 |
| `-o DIR` / `--output-dir DIR` | 输出目录，默认当前目录 |
| `--overwrite` | 覆盖已有文件；默认跳过 |
| `--timeout SECONDS` | 每个请求的超时，默认 30 秒 |
| `--json` | 输出一个 JSON 结果对象，便于其他程序调用 |
| `--verbose` | 输出诊断日志 |
| `--version` / `--help` | 查看版本或帮助 |

批量下载遇到一个器件失败时，会继续处理其他器件；重复编号只处理一次。退出码：`0` 成功或跳过，`1` 下载/写入失败，`2` 参数错误，`130` 用户中断。

```bash
python jlc-downloader.py --ID C41427486 C2040 --json > result.json
```

## 开发与构建

`easyeda2kicad` 用于读取封装中的模型信息，Requests 用于查询接口和下载 STEP。普通元件接口查不到时，会尝试商城交互式 3D 预览所使用的封装查询接口。下载需要联网，且模型服务器需要提供对应 STEP 文件。

在 Windows 下自行构建两个版本：

```powershell
python -m pip install -r requirements.txt -r requirements-build.txt Flask
python -m unittest -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

输出为 `dist/jlc-downloader.exe` 和 `dist/jlc-downloader-python.zip`。构建脚本默认使用 PATH 中的 `python`，也支持通过 `-Python` 参数指定解释器。

原网页入口保留在 `downloader.py`，安装 Flask 后可运行 `python downloader.py`，访问 http://127.0.0.1:5000。

软件许可证见 [LICENSE](LICENSE)，第三方依赖说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
