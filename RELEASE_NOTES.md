鸣谢：本项目参考并基于 [wormyrocks/lcsc_step_downloader](https://github.com/wormyrocks/lcsc_step_downloader) 修改而来。

v0.4.0 新增自定义下载文件名：

```powershell
jlc-downloader --ID C41427486 --name "复位按键"
```

文件保存为当前目录中的 `复位按键.step`。

- 支持 `--name` / `-n`，中文和空格，以及 `.step` / `.stp` 扩展名；未写扩展名会自动补 `.step`。
- 自定义名称限一个物料；下载目录由 `-o` 指定，已有文件默认跳过，覆盖需加 `--overwrite`。
- 简化模型继续保留 `_simplified` 文件名标记。
- 不指定名称时保持原来的物料编号命名方式。

Python 函数也支持：

```python
from jlc_downloader import download_model
path = download_model("C41427486", filename="复位按键.step")
```

Release 仅提供两个附件：

- **jlc-downloader.exe**：Windows x64 程序，内置 Python 和运行依赖。替换旧 exe 后直接使用。
- **jlc-downloader-python.zip**：Python 源码版，自行安装依赖后运行：

```bash
python -m pip install easyeda2kicad==1.0.1 requests
python jlc-downloader.py --ID C41427486 --name "复位按键"
```

简化模型采用预设厚度，仅作外观参考。支持交互选择以及 `--simplified`、`--json` 自动化调用。
