# Strudel Voice：Linux 便携版使用说明

本说明适用于已经构建完成的 Linux 发布目录 `strudel-voice`。该目录内已包含：

- Strudel 前端页面；
- Python 后端及其依赖；
- 语音识别所需的本地模型；
- `strudel-voice` 启动程序；
- `install.sh` 首次安装脚本。

因此，**不需要**再执行 `pnpm i`、`pnpm build`、`pip install`、`uvicorn`，也不需要下载 Whisper 模型。

## 使用前提

- Ubuntu/Debian x86_64 桌面系统；
- 已登录图形桌面，并有可用的麦克风输入；
- 首次安装时可使用 `sudo` 和网络连接；
- 端口 `8787` 没有被其他程序占用。

## 首次运行

将整个 `strudel-voice` 文件夹复制到 Ubuntu，例如桌面。不要只复制其中的可执行文件，因为 `_internal`、模型和静态资源也必须一并保留。

打开终端后执行：

```bash
cd ~/Desktop/strudel-voice
chmod +x install.sh strudel-voice
./install.sh
./strudel-voice
```

`./install.sh` 只需在每台电脑首次运行一次。它会安装操作系统级音频依赖：`ffmpeg`、`libportaudio2` 和 `libsndfile1`。

启动成功后，在该 Ubuntu 系统的浏览器打开：

```text
http://127.0.0.1:8787/
```

## 之后启动

以后只需要：

```bash
cd ~/Desktop/strudel-voice
./strudel-voice
```

## 退出

在运行程序的终端按 `Ctrl+C` 即可停止服务。

## 验证服务是否正常

当程序正在运行时，另开一个终端执行：

```bash
wget -qO- http://127.0.0.1:8787/health
```

正常结果应包含：

```json
{"ok":true,"message":"backend is healthy"}
```

## 常见问题

### `Permission denied`

说明可执行权限在复制或解压时丢失。重新执行：

```bash
chmod +x install.sh strudel-voice
```

### 浏览器无法打开或提示端口被占用

检查并关闭占用 8787 端口的旧进程：

```bash
ss -ltnp | grep :8787
```

然后重新运行 `./strudel-voice`。

### 无法录音或没有麦克风

确认 Ubuntu 已识别麦克风，并在系统的声音设置中选择正确的输入设备。该便携版需要在带图形桌面、PipeWire 或 PulseAudio 音频会话的 Linux 环境中运行；纯 SSH 终端通常没有可用麦克风。

### 首次安装失败

确认系统是 Ubuntu/Debian、网络可用且当前账号可以使用 `sudo`。然后重新执行 `./install.sh`。
