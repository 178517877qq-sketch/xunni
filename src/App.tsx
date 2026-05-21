import {
  Activity,
  Archive,
  CheckCircle2,
  ChevronRight,
  Cloud,
  FileJson2,
  FolderOpen,
  Gauge,
  Github,
  ListChecks,
  Play,
  RefreshCw,
  RotateCcw,
  Save,
  Settings,
  SlidersHorizontal,
  UploadCloud,
  WifiOff
} from "lucide-react";
import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import {
  cloneFallbackState,
  isDesktopRuntime,
  loadDesktopState,
  openOutputFolder,
  restoreOutputBackup,
  saveDesktopConfig,
  type DesktopState,
  type FieldSpec,
  type StatusCard
} from "./lib/desktopState";
import { buildWorkflowCommand, runWorkflow, type WorkflowMode } from "./lib/workflow";

const navItems = [
  { id: "workbench", label: "工作台", icon: Gauge },
  { id: "results", label: "结果", icon: ListChecks },
  { id: "settings", label: "设置", icon: SlidersHorizontal },
  { id: "logs", label: "日志/帮助", icon: FolderOpen }
];

const settingsTabs = ["常用", "源池", "同步", "高级"] as const;

const actionTiles: Array<{
  mode: WorkflowMode;
  title: string;
  hint: string;
  icon: typeof Play;
  tone: string;
}> = [
  { mode: "optimize-only", title: "只运行优选", hint: "断开 VPN 后本地直连测速", icon: Play, tone: "blue" },
  { mode: "optimize-sync", title: "优选后自动上传", hint: "完成后按设置同步到 GitHub", icon: UploadCloud, tone: "cyan" },
  { mode: "sync-only", title: "上传到 GitHub", hint: "只同步当前 ip.txt", icon: Github, tone: "green" },
  { mode: "proxy-test", title: "测试 GitHub 代理", hint: "只验证代理通道", icon: Activity, tone: "teal" }
];

type PageId = (typeof navItems)[number]["id"];
type SettingsTab = (typeof settingsTabs)[number];
type LogTone = "neutral" | "info" | "success" | "warning" | "error";

interface LogEntry {
  time: string;
  text: string;
  tone: LogTone;
}

const pageTitles: Record<PageId, string> = {
  workbench: "工作台",
  results: "优选结果",
  settings: "应用设置",
  logs: "日志/帮助"
};

const statusIconMap: Record<string, typeof Play> = {
  VPN: WifiOff,
  IP: Cloud,
  "443": CheckCircle2,
  GH: Github
};

const statusToneMap: Record<string, string> = {
  red: "text-red-600",
  blue: "text-blue-700",
  teal: "text-teal-600",
  green: "text-emerald-600"
};

function nowLabel() {
  return new Intl.DateTimeFormat("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date());
}

function parentPath(pathname: string) {
  const match = pathname.replace(/\\/g, "/").match(/^(.*)\/[^/]+$/);
  return match?.[1] ? match[1].replace(/\//g, "\\") : ".";
}

function normalizeDraft(values: Record<string, unknown>) {
  const draft: Record<string, string | boolean> = {};
  for (const [key, value] of Object.entries(values)) {
    draft[key] = typeof value === "boolean" ? value : value == null ? "" : String(value);
  }
  return draft;
}

function iconForAccent(accent: string) {
  return statusIconMap[accent] ?? Cloud;
}

function IconBadge({ icon: Icon, tone }: { icon: typeof Play; tone: string }) {
  return (
    <div className={clsx("grid h-12 w-12 place-items-center rounded-2xl border", `badge-${tone}`)}>
      <Icon size={22} strokeWidth={2.4} />
    </div>
  );
}

function ActionTile({
  tile,
  onRun,
  busy
}: {
  tile: (typeof actionTiles)[number];
  busy: boolean;
  onRun: (mode: WorkflowMode) => void;
}) {
  const command = buildWorkflowCommand(tile.mode);
  const Icon = tile.icon;
  return (
    <button
      className={clsx("action-tile group text-left", busy && "is-busy")}
      title={`${command.program} ${command.args.join(" ")}`}
      aria-busy={busy}
      onClick={() => onRun(tile.mode)}
    >
      <IconBadge icon={Icon} tone={tile.tone} />
      <span className="min-w-0">
        <span className="block text-[15px] font-semibold leading-5 text-slate-950">{tile.title}</span>
        <span className="mt-1 block text-[12px] leading-5 text-slate-500">{tile.hint}</span>
      </span>
    </button>
  );
}

function StatusRow({
  card
}: {
  card: StatusCard;
}) {
  const Icon = iconForAccent(card.icon);
  return (
    <div className="status-row">
      <IconBadge icon={Icon} tone={card.accent} />
      <div className="min-w-0">
        <div className="text-[12px] font-semibold text-slate-500">{card.title}</div>
        <div className={clsx("mt-1 text-[16px] font-bold", statusToneMap[card.accent] ?? "text-blue-700")}>
          {card.value}
        </div>
      </div>
      <div className="ml-auto text-right text-[12px] text-slate-500">{card.detail}</div>
    </div>
  );
}

function SettingRow({
  spec,
  value,
  onChange
}: {
  spec: FieldSpec;
  value: string | boolean;
  onChange: (name: string, next: string | boolean) => void;
}) {
  const isBoolean = spec.kind === "bool";
  const inputType = spec.kind === "int" || spec.kind === "float" ? "number" : "text";

  return (
    <div className="settings-line">
      <span>
        <strong>{spec.label}</strong>
        <small>
          字段 {spec.name} · {spec.kind}
        </small>
      </span>
      {isBoolean ? (
        <label className="setting-toggle">
          <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(spec.name, event.target.checked)} />
          <span>{value ? "开启" : "关闭"}</span>
        </label>
      ) : (
        <input
          type={inputType}
          step={spec.kind === "float" ? "any" : "1"}
          value={String(value ?? "")}
          onChange={(event) => onChange(spec.name, event.target.value)}
        />
      )}
    </div>
  );
}

function WorkbenchPage({
  state,
  lastCommand,
  onRun,
  busyAction,
  onRefreshState,
  onSaveSettings
}: {
  state: DesktopState;
  lastCommand: string;
  busyAction: WorkflowMode | "refresh" | "save" | "restore" | null;
  onRun: (mode: WorkflowMode) => void;
  onRefreshState: () => void;
  onSaveSettings: () => void;
}) {
  const cards = state.cards.length ? state.cards : cloneFallbackState().cards;
  const preflightLines = state.preflight.text.split("\n");

  return (
    <div className="dashboard-grid">
      <section className="space-y-5">
        <article className="glass-panel rounded-[32px] p-6">
          <div className="flex items-start gap-5">
            <div className="grid h-16 w-16 place-items-center rounded-2xl border border-blue-200 bg-blue-100 text-xl font-black text-blue-700">
              cf
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-[25px] font-black text-slate-950">Cloudflare IP 优选任务</h2>
                  <p className="mt-2 text-sm text-slate-500">直连测速，代理上传</p>
                </div>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">
                  手动流程
                </span>
              </div>

              <div className="action-grid mt-7 grid grid-cols-2 gap-4">
                {actionTiles.map((tile) => (
                  <ActionTile
                    key={tile.mode}
                    tile={tile}
                    busy={busyAction === tile.mode}
                    onRun={onRun}
                  />
                ))}
              </div>
            </div>
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">工具</h3>
          <div className="tool-grid mt-4 grid grid-cols-3 gap-4">
            <button className="danger-button" disabled title="当前版本未接入后台任务中止">
              停止任务
            </button>
            <button className="secondary-button" onClick={() => onSaveSettings()}>
              保存设置
            </button>
            <button className="secondary-button" onClick={() => onRefreshState()}>
              刷新状态
            </button>
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">最新结果预览</h3>
          <p className="mt-2 text-sm text-slate-500">443 优先输出，客户端继续二次优选。</p>
          <div className="mt-4 flex flex-wrap gap-7 text-sm">
            <span className="text-slate-500">
              节点数 <strong className="ml-2 text-lg text-slate-950">{state.output_count}</strong>
            </span>
            <span className="text-slate-500">
              443 占比 <strong className="ml-2 text-lg text-blue-700">{state.port_share}</strong>
            </span>
            <span className="text-slate-500">
              更新时间 <strong className="ml-2 text-slate-950">{state.output_updated_at ?? "未生成"}</strong>
            </span>
          </div>
          <pre className="preview-list">{state.output_preview.join("\n")}</pre>
        </article>
      </section>

      <section className="space-y-5">
        <article className="glass-panel rounded-[32px] p-5">
          <h3 className="section-title">当前状态</h3>
          <div className="mt-4 divide-y divide-slate-200/80">
            {cards.map((card) => (
              <StatusRow key={card.title} card={card} />
            ))}
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">运行前检查</h3>
          <div className={clsx("terminal-card", state.preflight.has_warnings && "has-warning")}>
            {preflightLines.map((line) => (
              <div key={line}>{line}</div>
            ))}
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">运行日志</h3>
          <div className="empty-log">{lastCommand}</div>
        </article>
      </section>
    </div>
  );
}

function ResultsPage({
  state,
  selectedBackup,
  onSelectBackup,
  onRestoreBackup,
  busyAction
}: {
  state: DesktopState;
  selectedBackup: string | null;
  onSelectBackup: (path: string) => void;
  onRestoreBackup: () => void;
  busyAction: WorkflowMode | "refresh" | "save" | "restore" | null;
}) {
  return (
    <div className="results-grid">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">ip.txt</h3>
        <p className="mt-2 text-sm text-slate-500">最终订阅源内容，格式保持 IP:port#CC。</p>
        <div className="mt-4 flex flex-wrap gap-6 text-sm">
          <span className="text-slate-500">
            总数 <strong className="ml-2 text-lg text-slate-950">{state.output_count}</strong>
          </span>
          <span className="text-slate-500">
            443 占比 <strong className="ml-2 text-lg text-blue-700">{state.port_share}</strong>
          </span>
          <span className="text-slate-500">
            更新时间 <strong className="ml-2 text-slate-950">{state.output_updated_at ?? "未生成"}</strong>
          </span>
        </div>
        <pre className="preview-list min-h-[360px]">{state.output_preview.join("\n")}</pre>
      </article>
      <article className="glass-panel rounded-[30px] p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="section-title">历史备份</h3>
            <p className="mt-2 text-sm text-slate-500">恢复前会先备份当前 ip.txt。</p>
          </div>
          <button className="soft-button" onClick={onRestoreBackup} disabled={!selectedBackup || busyAction === "restore"}>
            <RotateCcw size={16} />
            恢复
          </button>
        </div>

        <div className="backup-list">
          {state.backups.length ? (
            state.backups.map((item) => (
              <button
                key={item.path}
                className={clsx("backup-item", selectedBackup === item.path && "selected")}
                onClick={() => onSelectBackup(item.path)}
              >
                <span>{item.name}</span>
                <small>
                  {item.modified_at ?? "未知时间"} · {item.size} B
                </small>
              </button>
            ))
          ) : (
            <div className="empty-log">暂无备份</div>
          )}
        </div>
      </article>
    </div>
  );
}

function SettingsPage({
  state,
  activeSettingsTab,
  setActiveSettingsTab,
  commonDraft,
  onChangeDraft,
  rawDraft,
  onChangeRawDraft,
  onLoad,
  onSave,
  onOpenConfigFolder,
  busyAction
}: {
  state: DesktopState;
  activeSettingsTab: SettingsTab;
  setActiveSettingsTab: (tab: SettingsTab) => void;
  commonDraft: Record<string, string | boolean>;
  onChangeDraft: (name: string, next: string | boolean) => void;
  rawDraft: string;
  onChangeRawDraft: (value: string) => void;
  onLoad: () => void;
  onSave: () => void;
  onOpenConfigFolder: () => void;
  busyAction: WorkflowMode | "refresh" | "save" | "restore" | null;
}) {
  const activeFieldSpecs = useMemo(
    () => state.field_specs.filter((spec) => spec.section === activeSettingsTab),
    [activeSettingsTab, state.field_specs]
  );

  return (
    <div className="space-y-5">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">配置文件</h3>
        <div className="settings-row">
          <span>
            <strong>路径</strong>
            <small>当前 config.json 位置</small>
          </span>
          <strong>{state.config_path}</strong>
          <button className="soft-button" onClick={onLoad} disabled={busyAction === "refresh"}>
            加载
          </button>
          <button className="secondary-button" onClick={onSave} disabled={busyAction === "save"}>
            保存
          </button>
        </div>
        <div className="settings-row">
          <span>
            <strong>Python</strong>
            <small>当前运行解释器</small>
          </span>
          <strong className="truncate">{state.python_exe}</strong>
          <button className="secondary-button" onClick={onOpenConfigFolder}>
            浏览
          </button>
        </div>
      </article>

      <article className="glass-panel rounded-[30px] p-5">
        <div className="settings-tabs">
          {settingsTabs.map((tab) => (
            <button key={tab} className={clsx(tab === activeSettingsTab && "active")} onClick={() => setActiveSettingsTab(tab)}>
              {tab}
            </button>
          ))}
        </div>

        {activeSettingsTab === "高级" ? (
          <div className="editor-shell">
            <div className="editor-header">
              <FileJson2 size={16} />
              <span>完整 JSON 兜底编辑器</span>
            </div>
            <textarea
              className="json-editor"
              value={rawDraft}
              onChange={(event) => onChangeRawDraft(event.target.value)}
              spellCheck={false}
            />
          </div>
        ) : (
          <div className="settings-fields">
            {activeFieldSpecs.map((spec) => (
              <SettingRow
                key={spec.name}
                spec={spec}
                value={commonDraft[spec.name] ?? state.config[spec.name] ?? ""}
                onChange={onChangeDraft}
              />
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function LogsPage({ entries }: { entries: LogEntry[] }) {
  return (
    <div className="results-grid">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">完整运行日志</h3>
        <div className="terminal-card min-h-[420px]">
          {entries.length ? (
            entries.map((entry) => (
              <div key={`${entry.time}-${entry.text}`} className={clsx("log-line", `tone-${entry.tone}`)}>
                <span>[{entry.time}]</span>
                <span>{entry.text}</span>
              </div>
            ))
          ) : (
            <div>等待任务运行...</div>
          )}
        </div>
      </article>
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">手动流程</h3>
        <div className="help-flow">
          <p>1. 优选前断开 VPN，测速走本地直连。</p>
          <p>2. 只运行优选生成本地 ip.txt。</p>
          <p>3. 打开代理后上传到 GitHub。</p>
          <p>4. 客户端继续做二次优选。</p>
        </div>
      </article>
    </div>
  );
}

function App() {
  const fallback = useMemo(() => cloneFallbackState(), []);
  const [activePage, setActivePage] = useState<PageId>("workbench");
  const [activeSettingsTab, setActiveSettingsTab] = useState<SettingsTab>("常用");
  const [desktopState, setDesktopState] = useState<DesktopState>(fallback);
  const [commonDraft, setCommonDraft] = useState<Record<string, string | boolean>>(normalizeDraft(fallback.common_values));
  const [rawDraft, setRawDraft] = useState(JSON.stringify(fallback.config, null, 2));
  const [selectedBackup, setSelectedBackup] = useState<string | null>(fallback.backups[0]?.path ?? null);
  const [lastCommand, setLastCommand] = useState("等待手动操作");
  const [stateError, setStateError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<WorkflowMode | "refresh" | "save" | "restore" | null>(null);
  const [activityLog, setActivityLog] = useState<LogEntry[]>([
    { time: nowLabel(), text: "等待手动操作", tone: "neutral" }
  ]);

  const pythonPath = desktopState.python_exe || "python";
  const proxyUrl = String(desktopState.config.GITHUB_SYNC_PROXY_URL ?? "").trim();
  const canRunNative = isDesktopRuntime();
  const openConfigFolderTarget = useMemo(() => parentPath(desktopState.config_path), [desktopState.config_path]);

  function pushLog(text: string, tone: LogTone = "info") {
    setActivityLog((current) => [{ time: nowLabel(), text, tone }, ...current].slice(0, 12));
  }

  async function refreshState(reason = "刷新检查") {
    setBusyAction("refresh");
    setStateError(null);
    try {
      const nextState = await loadDesktopState(pythonPath);
      setDesktopState(nextState);
      setCommonDraft(normalizeDraft(nextState.common_values));
      setRawDraft(JSON.stringify(nextState.config, null, 2));
      setSelectedBackup((current) => {
        if (current && nextState.backups.some((item) => item.path === current)) {
          return current;
        }
        return nextState.backups[0]?.path ?? null;
      });
      const summary = nextState.preflight.has_warnings ? "存在预检提示" : "状态正常";
      setLastCommand(`${reason}: ${summary}`);
      pushLog(`${reason}完成：${summary}`, nextState.preflight.has_warnings ? "warning" : "success");
    } catch (error) {
      const message = String(error);
      setStateError(message);
      setLastCommand(`${reason}失败：${message}`);
      pushLog(`${reason}失败：${message}`, "error");
    } finally {
      setBusyAction(null);
    }
  }

  useEffect(() => {
    void refreshState("初始加载");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRun(mode: WorkflowMode) {
    const workflow = buildWorkflowCommand(mode, {
      pythonPath,
      proxyUrl
    });
    const commandText = `${workflow.program} ${workflow.args.join(" ")}`;
    setLastCommand(`${workflow.label}: ${commandText}`);
    pushLog(`${workflow.label} 已触发`, "info");

    if (!canRunNative) {
      return;
    }

    if (mode === "proxy-test" && !proxyUrl) {
      const warning = "未配置 GITHUB_SYNC_PROXY_URL，先去同步设置补上代理再测。";
      setLastCommand(warning);
      setStateError(warning);
      pushLog(warning, "warning");
      return;
    }

    setBusyAction(mode);
    setStateError(null);
    try {
      const result = await runWorkflow(mode, {
        pythonPath,
        proxyUrl
      });
      const stdout = String(result.stdout ?? "").trim();
      const stderr = String(result.stderr ?? "").trim();
      const tail = stdout ? stdout.split(/\r?\n/).filter(Boolean).slice(-1)[0] : "";
      if (result.code === 0) {
        const summary = tail || `${workflow.label} 已完成`;
        setLastCommand(summary);
        pushLog(summary, "success");
      } else {
        const summary = stderr || stdout || `${workflow.label} 失败，退出码 ${result.code}`;
        setLastCommand(summary);
        setStateError(summary);
        pushLog(summary, "error");
      }
    } catch (error) {
      const message = `${workflow.label} 启动失败：${String(error)}`;
      setLastCommand(message);
      setStateError(message);
      pushLog(message, "error");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSaveConfig() {
    setBusyAction("save");
    setStateError(null);
    try {
      if (activeSettingsTab === "高级") {
        const parsed = JSON.parse(rawDraft);
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error("高级 JSON 必须是对象");
        }
        await saveDesktopConfig({ mode: "raw", config: parsed as Record<string, unknown> }, pythonPath);
      } else {
        await saveDesktopConfig({ mode: "common", values: commonDraft }, pythonPath);
      }
      const summary = "配置已保存";
      setLastCommand(summary);
      pushLog(summary, "success");
      await refreshState("保存后刷新");
    } catch (error) {
      const message = `保存配置失败：${String(error)}`;
      setStateError(message);
      setLastCommand(message);
      pushLog(message, "error");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRestoreBackup() {
    if (!selectedBackup) {
      const message = "先选一个备份再恢复。";
      setStateError(message);
      setLastCommand(message);
      pushLog(message, "warning");
      return;
    }

    setBusyAction("restore");
    setStateError(null);
    try {
      const result = await restoreOutputBackup(selectedBackup, pythonPath);
      const summary = `已恢复 ${result.restored_path}`;
      setLastCommand(summary);
      pushLog(summary, "success");
      await refreshState("恢复后刷新");
    } catch (error) {
      const message = `恢复备份失败：${String(error)}`;
      setStateError(message);
      setLastCommand(message);
      pushLog(message, "error");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleOpenOutputFolder() {
    try {
      await openOutputFolder(parentPath(desktopState.output_path));
      pushLog(`已打开输出目录：${parentPath(desktopState.output_path)}`, "info");
    } catch (error) {
      const message = `打开输出目录失败：${String(error)}`;
      setStateError(message);
      pushLog(message, "error");
    }
  }

  async function handleOpenConfigFolder() {
    try {
      await openOutputFolder(openConfigFolderTarget);
      pushLog(`已打开配置目录：${openConfigFolderTarget}`, "info");
    } catch (error) {
      const message = `打开配置目录失败：${String(error)}`;
      setStateError(message);
      pushLog(message, "error");
    }
  }

  let pageContent = <LogsPage entries={activityLog} />;
  if (activePage === "workbench") {
    pageContent = (
      <WorkbenchPage
        state={desktopState}
        lastCommand={lastCommand}
        onRun={handleRun}
        busyAction={busyAction}
        onRefreshState={() => void refreshState("刷新检查")}
        onSaveSettings={() => void handleSaveConfig()}
      />
    );
  } else if (activePage === "results") {
    pageContent = (
      <ResultsPage
        state={desktopState}
        selectedBackup={selectedBackup}
        onSelectBackup={setSelectedBackup}
        onRestoreBackup={() => void handleRestoreBackup()}
        busyAction={busyAction}
      />
    );
  } else if (activePage === "settings") {
    pageContent = (
      <SettingsPage
        state={desktopState}
        activeSettingsTab={activeSettingsTab}
        setActiveSettingsTab={setActiveSettingsTab}
        commonDraft={commonDraft}
        onChangeDraft={(name, next) => setCommonDraft((current) => ({ ...current, [name]: next }))}
        rawDraft={rawDraft}
        onChangeRawDraft={setRawDraft}
        onLoad={() => void refreshState("手动加载")}
        onSave={() => void handleSaveConfig()}
        onOpenConfigFolder={() => void handleOpenConfigFolder()}
        busyAction={busyAction}
      />
    );
  }

  const primaryNotice = desktopState.preflight.has_warnings ? "请先断开 VPN" : "状态正常";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <button className={clsx("sidebar-refresh", busyAction === "refresh" && "is-busy")} title="刷新状态" onClick={() => void refreshState("刷新检查")}>
          <RefreshCw size={20} className={busyAction === "refresh" ? "animate-spin" : ""} />
        </button>
        <nav className="sidebar-rail">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={clsx("sidebar-item", activePage === item.id && "active")}
                aria-label={`侧栏-${item.label}`}
                title={item.label}
                onClick={() => setActivePage(item.id)}
              >
                <Icon size={20} />
              </button>
            );
          })}
          <span className="mt-auto pb-5 text-[12px] text-slate-400">手动</span>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1 className="text-[28px] font-black tracking-normal text-blue-700">{pageTitles[activePage]}</h1>
            <p className="mt-2 text-sm text-slate-500">配置已加载 · 手动工具模式</p>
          </div>

          <nav className="page-tabs">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  className={clsx("page-tab", activePage === item.id && "active")}
                  aria-current={activePage === item.id ? "page" : undefined}
                  onClick={() => setActivePage(item.id)}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="notice-pill">
            <span>提示</span>
            <strong>{primaryNotice}</strong>
            <button
              onClick={() => {
                setActivePage("settings");
                setActiveSettingsTab("同步");
              }}
            >
              <Settings size={14} />
              代理
            </button>
          </div>
        </header>

        <section className="workflow-strip">
          <span>
            <Gauge size={16} /> 本地直连测速
          </span>
          <span>
            <Github size={16} /> GitHub 代理上传
          </span>
          <span>
            <Archive size={16} /> 备份保护
          </span>
          <div className="ml-auto flex gap-3">
            <button className="ghost-button" onClick={() => void refreshState("刷新检查")} disabled={busyAction === "refresh"}>
              <RefreshCw size={16} className={busyAction === "refresh" ? "animate-spin" : ""} />
              刷新检查
            </button>
            <button className="secondary-button" onClick={() => void handleSaveConfig()} disabled={busyAction === "save"}>
              <Save size={16} />
              保存配置
            </button>
            <button className="soft-button" onClick={() => void handleOpenOutputFolder()}>
              <FolderOpen size={16} />
              输出目录
            </button>
          </div>
        </section>

        {stateError ? <div className="state-banner state-banner--error">{stateError}</div> : null}

        <div key={activePage} className="page-stage">
          {pageContent}
        </div>
      </section>
    </main>
  );
}

export default App;
