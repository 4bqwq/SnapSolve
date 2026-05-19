# SnapSolve

屏幕截图问答工具：按全局快捷键截取主屏，快路 VLM 和慢路 VLM+LLM 并发生成答案，并通过浏览器 SSE 页面实时显示。

## 使用

1. 安装依赖：

   ```powershell
   uv sync
   ```

2. 创建配置：

   ```powershell
   cp config.example.toml config.toml
   ```

3. 编辑 `config.toml`，分别填入 VLM 和 LLM 的 OpenAI 兼容 Chat Completions API 配置。

4. 启动：

   ```powershell
   uv run snapsolve
   ```

启动后服务只监听端口，不自动打开浏览器。手动打开 `http://127.0.0.1:8765/` 查看输出页面。默认快捷键是 `Alt + Space`，每次触发都会新建一个题目标签页；页面内可用左右方向键切换标签。

## 上下文

快路 VLM 和慢路 LLM 分别维护独立上下文。上下文只保存在当前服务进程内存中：每次启动服务器后从空上下文开始累计；按 `Ctrl+C` 关闭后上下文直接丢弃，重新启动不会继承上次提问历史。

## 配置要点

- `[server]`：服务监听地址和端口。
- `[vlm_api]`：快路回答和截图文字提取使用的视觉模型 API。
- `[llm_api]`：慢路深度推理使用的文本模型 API。

## 接口

- `GET /`：输出页面
- `GET /events`：SSE 事件流
- `POST /capture`：手动触发一次截图
- `GET /health`：健康检查
