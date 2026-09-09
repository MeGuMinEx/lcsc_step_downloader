鸣谢：本项目参考并基于 [wormyrocks/lcsc_step_downloader](https://github.com/wormyrocks/lcsc_step_downloader) 修改而来。

本 Release 提供两个版本：

- **jlc-downloader.exe**：Windows x64 独立程序，已内置 Python 和依赖，下载即可运行。
- **jlc-downloader-python.zip**：Python 源码包，解压后自行安装依赖并运行 .py 文件。

### exe 版

```powershell
.\jlc-downloader.exe --ID C41427486
```

将 exe 所在文件夹加入 PATH 后：

```powershell
jlc-downloader --ID C41427486
```

### Python 版

在解压后的源码目录执行：

```bash
python -m pip install easyeda2kicad==1.0.1 requests
python jlc-downloader.py --ID C41427486
```

也支持函数调用：

```python
from jlc_downloader import download_model
path = download_model("C41427486")
```

两种版本都默认保存到命令行当前目录，支持批量编号、`-o`、`--overwrite`、`--timeout` 和 `--json`。STEP 文件保留模型服务器提供的颜色定义。
