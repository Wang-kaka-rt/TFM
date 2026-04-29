# Strudel 实时语音采样系统开发清单

## 开发语言与技术栈
- 后端主语言：Python 3.10+
- 后端框架：FastAPI（提供录音控制、状态查询、采样服务接口）
- 前端/集成语言：JavaScript（在 Strudel 中封装 `start/reload/stop` 命令）
- 音频处理：FFmpeg + pydub
- 语音识别：faster-whisper（实时模式），WhisperX（会话后精修，可选）
- 语音活动检测：Silero VAD
- 数据格式：JSON（`metadata.json`、`samples.json`）

## 目录建议
```text
TFM/
  backend/
  strudel/
  samples/
  scripts/
```

## Sprint 0：原型验证（1 周）
- 搭建最小工程骨架与依赖环境
- 在 Strudel 中验证自定义函数注入与本地 HTTP 调用
- 启动 FastAPI 空服务与健康检查接口
- 打通 `start("test01")` 到后端响应
- 验收标准：Strudel 能成功调用本地接口并返回状态

## Sprint 1：MVP 闭环（1-2 周）
- 实现 `/start`、`/stop`、`/status` 与会话管理
- 实现麦克风采集与 2.5-3.0 秒音频分块（保存到 `raw/`）
- 集成 faster-whisper 词级时间戳
- 按词级边界切割并输出 `words/`
- 生成 `metadata.json`、`samples.json`、`strudel.js`
- 验收标准：完成 `start -> reload -> stop` 后可立即在 Strudel 播放新采样

## Sprint 2：多层级分割（1-2 周）
- 集成 Silero VAD 过滤静音/噪声段
- 实现 NLP 聚合逻辑：词 -> 短语 -> 句子
- 输出 `phrases/`、`sentences/`，统一命名规则
- 支持 `reload` 增量更新采样映射
- 验收标准：可在 Strudel 同时调用词级、短语级、句子级采样

## Sprint 3：精度增强（1 周）
- 加入双模式 ASR 策略：
- 实时模式：faster-whisper（低延迟）
- 精修模式：WhisperX 后台异步强制对齐（高精度）
- 实现精修结果回写与替换策略
- 验收标准：不影响实时演出的前提下提升切割边界精度

## Sprint 4：稳定性与工程化（1 周）
- 补齐 `/strudel/{session}` 与 `/samples/{session}/...` 静态服务
- 完善异常处理：设备占用、空音频、ASR 超时、路径异常
- 增加关键测试：接口流、分割质量、并发会话、回归测试
- 增加日志指标：每块处理延迟、切割可用率
- 验收标准：满足提案性能目标，可连续稳定演示

## 推荐里程碑交付
- M1：完成原型通信与空后端
- M2：完成 MVP 可录可播闭环
- M3：完成短语/句子多层级采样
- M4：完成双模式 ASR 与性能优化
- M5：完成测试文档与论文实验数据整理

## Sprint 5：封装为 EXE（1 周）
- 目标：将 Strudel 前端与 Python 后端整合为可双击启动的 Windows EXE 应用
- 打包方案：`PyInstaller + PyWebView + FastAPI`（优先采用单机离线可运行模式）
- 启动流程：EXE 启动后自动拉起本地后端服务，并加载本地 Strudel 页面
- 资源打包：包含 `ffmpeg`、模型文件、默认配置、静态前端文件
- 通信方式：统一走 `localhost`（如 `127.0.0.1:8787`）并配置 CORS 白名单
- 稳定性处理：端口占用检测、服务启动重试、异常提示与日志落盘
- 安全与兼容：限制仅本机访问，避免对公网暴露；处理首次模型加载耗时提示
- 交付物：`installer.exe`（或 `portable.exe`）、安装说明、启动与故障排查文档
- 验收标准：在无 Python 环境的 Windows 机器上可完成 `start -> reload -> stop -> 播放` 全流程
