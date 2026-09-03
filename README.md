# Local Pick

从本机几个文件夹里随机抽一项，然后用系统默认程序打开，或在资源管理器中定位。

适合媒体库、游戏目录这类「文件夹太多、每次不知道打开哪个」的情况。大类数量不写死，设置里可以加、改路径、改打开方式。

## 使用

Windows 上双击项目目录里的 `LocalPick.exe`。第一次运行会在 exe 旁边生成 `config.json`，到软件的「设置路径和大类」里填你自己的文件夹。

没有现成 exe、本机有 Python 3.10+ 时：

```text
python app.py
```

`config.json` 是你的本地配置（路径、上次抽中的项目），不要提交到 Git、不要放进网盘公开包。

## 行为

- 启动时可以自己点一个大类，也可以让程序在可用大类里等概率抽一个。
- 在当前文件夹的直接子项里抽一次。抽中文件就结束；抽中文件夹可以再抽一层，或打开/定位。
- 没有「换一个」。不满意就从头再来。
- 每个大类记住一条上次路径，打开或定位之后才会写入。
- `file` 模式：文件可直接打开。`folder_only` 模式（例如游戏）：只打开文件夹，不启动 exe。

候选池只包含子文件夹，以及该大类配置的扩展名。隐藏项和名为 `DwnlData` 的目录会被跳过。图包可以把扩展名设成 `.jpg, .png`。

## 从源码打包

```text
python -m pip install -r requirements-dev.txt
.\build.ps1
```

完成后 `LocalPick.exe` 会出现在项目根目录（和 README 同一层）。

## 开发

```text
python -m unittest tests.test_core
```

运行时代码只用 Python 标准库。`requirements-dev.txt` 里的 PyInstaller 仅用于打包。

## 许可

MIT
