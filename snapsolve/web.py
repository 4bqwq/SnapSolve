INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SnapSolve</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f7;
      --panel: #ffffff;
      --panel-alt: #fbfcfb;
      --line: #d9dfdc;
      --text: #1f2522;
      --muted: #66706a;
      --fast: #287866;
      --slow: #9a641c;
      --active: #111513;
      --shadow: 0 1px 2px rgba(17, 21, 19, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      height: 100%;
      margin: 0;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      overflow: hidden;
    }

    .app {
      display: grid;
      grid-template-rows: 48px 44px 1fr;
      height: 100vh;
      min-width: 320px;
      outline: none;
    }

    .topbar {
      align-items: center;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 16px;
      padding: 0 18px;
      box-shadow: var(--shadow);
    }

    .brand {
      font-size: 16px;
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
    }

    .connection {
      color: var(--muted);
      font-size: 12px;
      margin-left: auto;
      min-width: 56px;
      text-align: right;
    }

    .tabs {
      align-items: stretch;
      background: #eef1ef;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 1px;
      overflow-x: auto;
      overflow-y: hidden;
      scrollbar-width: thin;
    }

    .tab {
      appearance: none;
      background: transparent;
      border: 0;
      border-right: 1px solid var(--line);
      color: var(--muted);
      cursor: default;
      flex: 0 0 auto;
      font: inherit;
      font-size: 13px;
      min-width: 104px;
      outline: none;
      padding: 0 14px;
    }

    .tab.active {
      background: var(--panel);
      color: var(--active);
      font-weight: 650;
    }

    .empty-tabs {
      align-items: center;
      color: var(--muted);
      display: flex;
      font-size: 13px;
      padding: 0 18px;
    }

    .panes {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      min-height: 0;
    }

    .pane {
      background: var(--panel);
      display: grid;
      grid-template-rows: 42px 1fr;
      min-width: 0;
      min-height: 0;
    }

    .slow-pane {
      grid-template-rows: 42px 160px 1fr;
    }

    .pane + .pane {
      border-left: 1px solid var(--line);
    }

    .pane-head {
      align-items: center;
      background: var(--panel-alt);
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 10px;
      padding: 0 16px;
    }

    .lane-title {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0;
      white-space: nowrap;
    }

    .lane-title.fast {
      color: var(--fast);
    }

    .lane-title.slow {
      color: var(--slow);
    }

    .lane-status {
      color: var(--muted);
      font-size: 12px;
      margin-left: auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .extract-panel {
      background: #f4f6f5;
      border-bottom: 1px solid var(--line);
      display: grid;
      grid-template-rows: 32px 1fr;
      min-height: 0;
    }

    .extract-head {
      align-items: center;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 10px;
      padding: 0 16px;
    }

    .extract-title {
      color: #40514a;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }

    .extract-status {
      color: var(--muted);
      font-size: 12px;
      margin-left: auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .extract-output {
      color: #2f3935;
      font: 12px/1.55 Consolas, "SFMono-Regular", "Microsoft YaHei UI", monospace;
      margin: 0;
      min-height: 0;
      overflow: auto;
      padding: 10px 14px 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .output {
      color: var(--text);
      font: 14px/1.65 Consolas, "SFMono-Regular", "Microsoft YaHei UI", monospace;
      margin: 0;
      min-height: 0;
      overflow: auto;
      padding: 18px 20px 28px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .placeholder {
      color: var(--muted);
    }

    @media (max-width: 760px) {
      .app {
        grid-template-rows: 46px 42px 1fr;
      }

      .panes {
        grid-template-columns: 1fr;
        grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
      }

      .pane + .pane {
        border-left: 0;
        border-top: 1px solid var(--line);
      }

      .slow-pane {
        grid-template-rows: 42px 118px minmax(0, 1fr);
      }

      .output {
        font-size: 13px;
        padding: 14px 16px 22px;
      }
    }
  </style>
</head>
<body>
  <div class="app" id="app" tabindex="0">
    <header class="topbar">
      <div class="brand">SnapSolve</div>
      <div class="connection" id="connection">连接中</div>
    </header>
    <nav class="tabs" id="tabs" aria-label="题目标签">
      <div class="empty-tabs">等待截图</div>
    </nav>
    <main class="panes">
      <section class="pane" aria-label="快路答案">
        <div class="pane-head">
          <span class="lane-title fast">快路</span>
          <span class="lane-status" id="fastStatus"></span>
        </div>
        <pre class="output placeholder" id="fastOutput"></pre>
      </section>
      <section class="pane slow-pane" aria-label="慢路答案">
        <div class="pane-head">
          <span class="lane-title slow">慢路</span>
          <span class="lane-status" id="slowStatus"></span>
        </div>
        <div class="extract-panel" aria-label="题目提取">
          <div class="extract-head">
            <span class="extract-title">题目提取</span>
            <span class="extract-status" id="extractStatus"></span>
          </div>
          <pre class="extract-output placeholder" id="extractOutput"></pre>
        </div>
        <pre class="output placeholder" id="slowOutput"></pre>
      </section>
    </main>
  </div>
  <script>
    const state = {
      tabs: [],
      activeTabId: null
    };

    const el = {
      app: document.getElementById("app"),
      tabs: document.getElementById("tabs"),
      connection: document.getElementById("connection"),
      fastOutput: document.getElementById("fastOutput"),
      slowOutput: document.getElementById("slowOutput"),
      extractOutput: document.getElementById("extractOutput"),
      fastStatus: document.getElementById("fastStatus"),
      slowStatus: document.getElementById("slowStatus"),
      extractStatus: document.getElementById("extractStatus")
    };

    function activeTab() {
      return state.tabs.find((tab) => tab.id === state.activeTabId) || null;
    }

    function statusText(status) {
      const map = {
        idle: "",
        waiting: "等待",
        running: "生成中",
        extracting: "提取中",
        extract: "识别中",
        thinking: "推理中",
        done: "完成",
        error: "错误"
      };
      return map[status] || status || "";
    }

    function renderTabs() {
      el.tabs.replaceChildren();
      if (state.tabs.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty-tabs";
        empty.textContent = "等待截图";
        el.tabs.appendChild(empty);
        return;
      }

      for (const tab of state.tabs) {
        const button = document.createElement("button");
        button.className = "tab" + (tab.id === state.activeTabId ? " active" : "");
        button.textContent = tab.title;
        button.type = "button";
        button.addEventListener("click", () => setActiveTab(tab.id));
        el.tabs.appendChild(button);
      }
    }

    function renderOutputs() {
      const tab = activeTab();
      if (!tab) {
        el.fastOutput.textContent = "";
        el.slowOutput.textContent = "";
        el.extractOutput.textContent = "";
        el.fastOutput.classList.add("placeholder");
        el.slowOutput.classList.add("placeholder");
        el.extractOutput.classList.add("placeholder");
        el.fastStatus.textContent = "";
        el.slowStatus.textContent = "";
        el.extractStatus.textContent = "";
        return;
      }

      el.fastOutput.textContent = tab.fast || "";
      el.slowOutput.textContent = tab.slow || "";
      el.extractOutput.textContent = tab.extract || "";
      el.fastOutput.classList.toggle("placeholder", !tab.fast);
      el.slowOutput.classList.toggle("placeholder", !tab.slow);
      el.extractOutput.classList.toggle("placeholder", !tab.extract);
      el.fastStatus.textContent = statusText(tab.statuses.fast);
      el.slowStatus.textContent = statusText(tab.statuses.slow);
      el.extractStatus.textContent = statusText(tab.statuses.extract);
      scrollToBottom();
    }

    function renderAll() {
      renderTabs();
      renderOutputs();
      el.app.focus({ preventScroll: true });
    }

    function scrollToBottom() {
      requestAnimationFrame(() => {
        el.fastOutput.scrollTop = el.fastOutput.scrollHeight;
        el.slowOutput.scrollTop = el.slowOutput.scrollHeight;
        el.extractOutput.scrollTop = el.extractOutput.scrollHeight;
      });
    }

    function setActiveTab(tabId) {
      if (!state.tabs.some((tab) => tab.id === tabId)) {
        return;
      }
      state.activeTabId = tabId;
      renderAll();
    }

    function moveTab(delta) {
      if (state.tabs.length === 0) {
        return;
      }
      const index = Math.max(0, state.tabs.findIndex((tab) => tab.id === state.activeTabId));
      const next = (index + delta + state.tabs.length) % state.tabs.length;
      setActiveTab(state.tabs[next].id);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        moveTab(-1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        moveTab(1);
      }
    });

    function upsertTab(tab) {
      const index = state.tabs.findIndex((existing) => existing.id === tab.id);
      if (index >= 0) {
        state.tabs[index] = { ...state.tabs[index], ...tab };
      } else {
        state.tabs.push(tab);
      }
    }

    const events = new EventSource("/events");

    events.addEventListener("open", () => {
      el.connection.textContent = "已连接";
    });

    events.addEventListener("error", () => {
      el.connection.textContent = "重连中";
    });

    events.addEventListener("snapshot", (event) => {
      const payload = JSON.parse(event.data);
      state.tabs = payload.tabs || [];
      state.activeTabId = payload.active_tab_id || (state.tabs.at(-1) || {}).id || null;
      renderAll();
    });

    events.addEventListener("tab_created", (event) => {
      const payload = JSON.parse(event.data);
      upsertTab(payload.tab);
      state.activeTabId = payload.active_tab_id || payload.tab.id;
      renderAll();
    });

    events.addEventListener("token", (event) => {
      const payload = JSON.parse(event.data);
      const tab = state.tabs.find((item) => item.id === payload.tab_id);
      if (!tab) {
        return;
      }
      tab[payload.lane] = (tab[payload.lane] || "") + payload.text;
      if (tab.id === state.activeTabId) {
        renderOutputs();
      }
    });

    events.addEventListener("status", (event) => {
      const payload = JSON.parse(event.data);
      const tab = state.tabs.find((item) => item.id === payload.tab_id);
      if (!tab) {
        return;
      }
      tab.statuses = tab.statuses || {};
      tab.statuses[payload.lane] = payload.status;
      if (payload.message) {
        tab[payload.lane] = (tab[payload.lane] || "") + payload.message;
      }
      if (tab.id === state.activeTabId) {
        renderOutputs();
      }
    });

    el.app.focus({ preventScroll: true });
  </script>
</body>
</html>
"""
