# MP3 压缩工具

基于 PySide6 的跨平台 MP3 批量压缩桌面工具，内置 FFmpeg，无需用户单独安装。

## 功能

- 选择源文件夹与目标文件夹，批量压缩目录内所有 `.mp3` 文件
- 默认使用推荐配置：`-ac 1 -codec:a libmp3lame -qscale:a 8`
- 支持预设：推荐 / 高压缩 / 高质量 / 自定义
- 自定义参数：声道、VBR 质量、固定比特率、采样率
- 文件任务列表：每个文件独立进度条、百分比、状态（等待中 / 压缩中 / 完成 / 失败）
- 压缩前后体积对比（单文件 + 汇总统计）
- 支持暂停、继续、停止、重试失败项

## 本地开发运行

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 下载当前平台 FFmpeg（首次需要）
python scripts/download_ffmpeg.py --platform macos   # 或 windows / linux

# 启动 GUI
python main.py
```

## 使用步骤

1. 选择源文件夹（包含 MP3 文件）
2. 选择目标文件夹（输出目录，不存在会自动创建）
3. 点击「扫描 MP3」加载文件列表
4. 确认压缩配置（默认已是推荐配置）
5. 点击「开始压缩」
6. 在任务列表中查看每个文件的进度与完成状态

## 打包

### 本地打包（当前系统）

```bash
python scripts/download_ffmpeg.py --platform auto
pyinstaller mp3-compressor.spec --noconfirm
```

- macOS 输出：`dist/MP3Compressor.app`
- Windows 输出：`dist/MP3Compressor/MP3Compressor.exe`

### GitHub Actions 双平台构建

推送代码到 `main` / `master` 分支，或在 Actions 页面手动触发 `Build MP3 Compressor` workflow。

构建完成后在 Artifacts 中下载：

- `MP3Compressor-macOS`
- `MP3Compressor-Windows`

## 项目结构

```
main.py                          # 程序入口
app/
  core/
    compression_profiles.py        # 预设与参数模型
    ffmpeg_runner.py             # 批量压缩与进度
    ffmpeg_path.py               # 内置 FFmpeg 路径解析
    file_scan.py                 # MP3 扫描
    size_report.py               # 体积格式化
  ui/
    main_window.py               # 主界面
resources/ffmpeg/                # 内置 FFmpeg 二进制
scripts/download_ffmpeg.py       # FFmpeg 下载脚本
mp3-compressor.spec              # PyInstaller 配置
.github/workflows/build.yml      # CI 双平台构建
```

## 推荐配置说明

等价于你当前使用的命令：

```bash
ffmpeg -i input.mp3 -ac 1 -codec:a libmp3lame -qscale:a 8 output.mp3
```

- 单声道：体积更小，适合语音/播客
- `qscale:a 8`：VBR 质量参数，数值越小音质越好、文件越大

## 常见问题

**Q: 提示未找到 FFmpeg？**  
A: 运行 `python scripts/download_ffmpeg.py --platform auto`，或确保系统 PATH 中已安装 `ffmpeg`。

**Q: macOS 提示无法打开应用？**  
A: 在「系统设置 → 隐私与安全性」中允许打开，或对 `.app` 执行 `xattr -cr dist/MP3Compressor.app`。

**Q: 压缩后文件反而变大？**  
A: 源文件可能已是低码率 MP3，可尝试「高压缩」预设或提高 qscale 数值。
