鸣谢：本项目参考并基于 [wormyrocks/lcsc_step_downloader](https://github.com/wormyrocks/lcsc_step_downloader) 修改而来。

本 Release 提供两个版本：

- **jlc-downloader.exe**：Windows x64 独立程序，已内置 Python 和依赖，下载即可运行。
- **jlc-downloader-python.zip**：Python 源码包，解压后自行安装依赖并运行 .py 文件。

新增无独立 3D 模型时的交互选择：

```text
1. 下载简化模型
2. 放弃下载简化模型
```

例如运行 `jlc-downloader --ID C49234121` 后选择 `1`，会生成 `C49234121_simplified.step`。选择 `2` 或直接回车则放弃，不创建文件。

简化模型按网页的本体/引脚轮廓和预设厚度生成，仅作外观参考。导出由纯 Python 实现，无需额外安装 CAD 软件或 CAD 运行库。目前支持直线多边形、圆形引脚和线段轮廓；复杂曲线及带孔轮廓暂不支持。

自动化调用可加 `--simplified`，Python 函数可加 `simplified=True`。JSON 模式不会弹出询问。

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
