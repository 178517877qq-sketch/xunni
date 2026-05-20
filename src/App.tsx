import {
  Activity,
  Archive,
  CheckCircle2,
  Cloud,
  FolderOpen,
  Gauge,
  Github,
  ListChecks,
  Play,
  RefreshCw,
  Settings,
  SlidersHorizontal,
  UploadCloud,
  WifiOff
} from "lucide-react";
import clsx from "clsx";
import { useMemo, useState } from "react";
import { buildWorkflowCommand, runWorkflow, type WorkflowMode } from "./lib/workflow";

const navItems = [
  { id: "workbench", label: "工作台", icon: Gauge },
  { id: "results", label: "结果", icon: ListChecks },
  { id: "settings", label: "设置", icon: SlidersHorizontal },
  { id: "logs", label: "日志/帮助", icon: FolderOpen }
];

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

const outputPreview = [
  "43.168.16.112:443#HK",
  "154.31.117.200:443#JP",
  "103.117.102.48:443#JP",
  "8.210.29.68:443#HK",
  "219.76.13.169:443#HK"
];

type PageId = (typeof navItems)[number]["id"];

const pageTitles: Record<PageId, string> = {
  workbench: "工作台",
  results: "优选结果",
  settings: "应用设置",
  logs: "日志/帮助"
};

function IconBadge({ icon: Icon, tone }: { icon: typeof Play; tone: string }) {
  return (
    <div className={clsx("grid h-12 w-12 place-items-center rounded-2xl border", `badge-${tone}`)}>
      <Icon size={22} strokeWidth={2.4} />
    </div>
  );
}

function ActionTile({ tile, onRun }: { tile: (typeof actionTiles)[number]; onRun: (mode: WorkflowMode) => void }) {
  const command = buildWorkflowCommand(tile.mode);
  const Icon = tile.icon;
  return (
    <button className="action-tile group text-left" title={`${command.program} ${command.args.join(" ")}`} onClick={() => onRun(tile.mode)}>
      <IconBadge icon={Icon} tone={tile.tone} />
      <span className="min-w-0">
        <span className="block text-[15px] font-semibold leading-5 text-slate-950">{tile.title}</span>
        <span className="mt-1 block text-[12px] leading-5 text-slate-500">{tile.hint}</span>
      </span>
    </button>
  );
}

function StatusRow({
  icon: Icon,
  label,
  value,
  detail,
  danger
}: {
  icon: typeof Play;
  label: string;
  value: string;
  detail: string;
  danger?: boolean;
}) {
  return (
    <div className="status-row">
      <IconBadge icon={Icon} tone={danger ? "red" : "blue"} />
      <div className="min-w-0">
        <div className="text-[12px] font-semibold text-slate-500">{label}</div>
        <div className={clsx("mt-1 text-[16px] font-bold", danger ? "text-red-600" : "text-blue-700")}>{value}</div>
      </div>
      <div className="ml-auto text-right text-[12px] text-slate-500">{detail}</div>
    </div>
  );
}

function WorkbenchPage({ lastCommand, onRun }: { lastCommand: string; onRun: (mode: WorkflowMode) => void }) {
  return (
    <div className="dashboard-grid">
      <section className="space-y-5">
        <article className="glass-panel rounded-[32px] p-6">
          <div className="flex items-start gap-5">
            <div className="grid h-16 w-16 place-items-center rounded-2xl border border-blue-200 bg-blue-100 text-xl font-black text-blue-700">cf</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-[25px] font-black text-slate-950">Cloudflare IP 优选任务</h2>
                  <p className="mt-2 text-sm text-slate-500">直连测速，代理上传</p>
                </div>
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700">手动流程</span>
              </div>

              <div className="mt-7 grid grid-cols-2 gap-4">
                {actionTiles.map((tile) => <ActionTile key={tile.mode} tile={tile} onRun={onRun} />)}
              </div>
            </div>
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">工具</h3>
          <div className="mt-4 grid grid-cols-3 gap-4">
            <button className="danger-button">停止任务</button>
            <button className="secondary-button">保存设置</button>
            <button className="secondary-button">刷新状态</button>
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">最新结果预览</h3>
          <p className="mt-2 text-sm text-slate-500">443 优先输出，客户端继续二次优选。</p>
          <div className="mt-4 flex gap-7 text-sm">
            <span className="text-slate-500">443 占比 <strong className="ml-2 text-lg text-blue-700">68%</strong></span>
            <span className="text-slate-500">更新时间 <strong className="ml-2 text-slate-950">2026-05-20 19:33:00</strong></span>
          </div>
          <pre className="preview-list">{outputPreview.join("\n")}</pre>
        </article>
      </section>

      <section className="space-y-5">
        <article className="glass-panel rounded-[32px] p-5">
          <h3 className="section-title">当前状态</h3>
          <div className="mt-4 divide-y divide-slate-200/80">
            <StatusRow icon={WifiOff} label="VPN/代理" value="请断开 VPN" detail="测速阶段保持本地直连" danger />
            <StatusRow icon={Cloud} label="当前 ip.txt" value="19" detail="2026-05-20 19:33:00" />
            <StatusRow icon={CheckCircle2} label="443 占比" value="68%" detail="443 优先输出" />
            <StatusRow icon={Github} label="GitHub" value="代理未配置" detail="上传阶段可单独走代理" />
          </div>
        </article>

        <article className="glass-panel rounded-[28px] p-5">
          <h3 className="section-title">运行前检查</h3>
          <div className="terminal-card">
            运行模式：工作台检查<br />
            检查结果<br />
            [OK] 配置文件存在：config.json<br />
            [OK] Python 可用<br />
            [OK] 输出目录存在<br />
            [WARN] 优选前请断开 VPN
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

function ResultsPage() {
  return (
    <div className="results-grid">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">ip.txt</h3>
        <p className="mt-2 text-sm text-slate-500">最终订阅源内容，格式保持 IP:port#CC。</p>
        <pre className="preview-list min-h-[360px]">{outputPreview.concat(outputPreview).join("\n")}</pre>
      </article>
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">历史备份</h3>
        <div className="backup-list">
          {["ip.txt.20260521-030803.bak", "ip.txt.20260520-193300.bak", "ip.txt.20260519-221400.bak"].map((item) => (
            <button key={item}>{item}</button>
          ))}
        </div>
      </article>
    </div>
  );
}

function SettingsPage() {
  return (
    <div className="space-y-5">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">配置文件</h3>
        <div className="settings-row"><span>路径</span><strong>config.json</strong><button className="soft-button">加载</button><button className="secondary-button">保存</button></div>
        <div className="settings-row"><span>Python</span><strong>python</strong><button className="secondary-button">浏览</button></div>
      </article>
      <article className="glass-panel rounded-[30px] p-5">
        <div className="settings-tabs"><button className="active">常用</button><button>源池</button><button>同步</button><button>高级</button></div>
        {["全局模式", "全局 TopN", "分国家 TopN", "带宽候选数"].map((item, index) => (
          <div className="settings-line" key={item}><span><strong>{item}</strong><small>使用 cockpit 风格列表布局管理参数。</small></span><input value={index === 0 ? "开启" : index === 1 ? "24" : index === 2 ? "5" : "500"} readOnly /></div>
        ))}
      </article>
    </div>
  );
}

function LogsPage() {
  return (
    <div className="results-grid">
      <article className="glass-panel rounded-[30px] p-5">
        <h3 className="section-title">完整运行日志</h3>
        <div className="terminal-card min-h-[420px]">等待任务运行...</div>
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
  const [activePage, setActivePage] = useState<PageId>("workbench");
  const [lastCommand, setLastCommand] = useState("等待手动操作");
  const title = useMemo(() => pageTitles[activePage], [activePage]);

  async function handleRun(mode: WorkflowMode) {
    const workflow = buildWorkflowCommand(mode);
    setLastCommand(`${workflow.label}: ${workflow.program} ${workflow.args.join(" ")}`);
    if ("__TAURI_INTERNALS__" in window) {
      try {
        await runWorkflow(mode);
      } catch (error) {
        setLastCommand(`${workflow.label} 启动失败：${String(error)}`);
      }
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <button className="sidebar-refresh" title="刷新状态">
          <RefreshCw size={20} />
        </button>
        <nav className="sidebar-rail">
          {navItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <button key={item.id} className={clsx("sidebar-item", activePage === item.id && "active")} title={item.label} onClick={() => setActivePage(item.id)}>
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
            <h1 className="text-[28px] font-black tracking-normal text-blue-700">{title}</h1>
            <p className="mt-2 text-sm text-slate-500">配置已加载 · 手动工具模式</p>
          </div>

          <nav className="page-tabs">
            {navItems.map((item, index) => {
              const Icon = item.icon;
              return (
                <button key={item.id} className={clsx("page-tab", activePage === item.id && "active")} onClick={() => setActivePage(item.id)}>
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="notice-pill">
            <span>提示</span>
            <strong>直连测速，代理上传</strong>
            <button>代理</button>
          </div>
        </header>

        <section className="workflow-strip">
          <span><Gauge size={16} /> 本地直连测速</span>
          <span><Github size={16} /> GitHub 代理上传</span>
          <span><Archive size={16} /> 备份保护</span>
          <div className="ml-auto flex gap-3">
            <button className="ghost-button">刷新检查</button>
            <button className="secondary-button">保存配置</button>
            <button className="soft-button">输出目录</button>
          </div>
        </section>
        {activePage === "workbench" && <WorkbenchPage lastCommand={lastCommand} onRun={handleRun} />}
        {activePage === "results" && <ResultsPage />}
        {activePage === "settings" && <SettingsPage />}
        {activePage === "logs" && <LogsPage />}
      </section>
    </main>
  );
}

export default App;
