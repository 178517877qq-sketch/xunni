import { Command, open } from "@tauri-apps/plugin-shell";

export interface BackupItem {
  name: string;
  path: string;
  modified_at: string | null;
  size: number;
}

export interface StatusCard {
  title: string;
  icon: string;
  value: string;
  detail: string;
  accent: string;
}

export interface PreflightReport {
  text: string;
  can_continue: boolean;
  has_warnings: boolean;
}

export interface FieldSpec {
  name: string;
  label: string;
  kind: string;
  section: string;
}

export interface DesktopState {
  config_path: string;
  python_exe: string;
  config: Record<string, unknown>;
  common_values: Record<string, unknown>;
  field_specs: FieldSpec[];
  field_groups: Record<string, string[]>;
  output_path: string;
  output_exists: boolean;
  output_updated_at: string | null;
  output_count: number;
  output_preview: string[];
  port_share: string;
  backups: BackupItem[];
  preflight: PreflightReport;
  cards: StatusCard[];
}

export interface SaveConfigPayload {
  mode: "common" | "raw";
  values?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface SaveResult {
  saved: Record<string, unknown>;
}

export interface RestoreResult {
  restored_path: string;
}

export interface ProxyTestResult {
  ok: boolean;
  proxy_url: string;
  message: string;
}

const BRIDGE_SCRIPT = "ui_bridge.py";

const fallbackState: DesktopState = {
  config_path: "config.json",
  python_exe: "python",
  config: {
    OUTPUT_FILE: "ip.txt",
    GITHUB_SYNC_PROXY_URL: "",
    BACKUP_OUTPUT_ENABLED: true,
    OUTPUT_BACKUP_DIR: "backups",
    OUTPUT_BACKUP_KEEP: 20
  },
  common_values: {
    USE_GLOBAL_MODE: true,
    GLOBAL_TOP_N: 24,
    PER_COUNTRY_TOP_N: 5,
    BANDWIDTH_CANDIDATES: 500,
    OUTPUT_NODE_LIMIT: 24,
    MIN_SUCCESS_RATE: 1,
    TIMEOUT: 2,
    TCP_PROBES: 3,
    BANDWIDTH_SIZE_MB: 0.5,
    TEST_AVAILABILITY: true,
    STABILITY_SCORING_ENABLED: true,
    FILTER_COUNTRIES_ENABLED: false,
    ENABLE_CF_OFFICIAL_IP_SAMPLING: false,
    CF_OFFICIAL_SAMPLE_PER_24: 3,
    CF_OFFICIAL_SAMPLE_PORTS: "443",
    LOCAL_SEED_FILES: "重要ip.txt, 全量ip.txt",
    ALLOWED_COUNTRIES: "US",
    FILTER_BLOCKED_COUNTRIES_ENABLED: true,
    BLOCKED_COUNTRIES: "BD, BI, BY, CD, CF, CN, CU, DE, ET, HK, IR, KP, LY, MO, NG, NL, PK, RU, SD, SO, SY, TH, TW, UA, VE, VN, YE, ZW",
    OUTPUT_FILE: "ip.txt",
    BACKUP_OUTPUT_ENABLED: true,
    OUTPUT_BACKUP_DIR: "backups",
    OUTPUT_BACKUP_KEEP: 20,
    STABILITY_STATS_FILE: "ip_stats.json",
    LOG_FILE: "cfnb.log",
    CF_ENABLED: true,
    DNS_UPDATE_TARGET_COUNT: 15,
    ENABLE_WXPUSHER: true,
    GITHUB_SYNC_ENABLED: true,
    GITHUB_SYNC_PROXY_URL: "",
    GITHUB_SYNC_MAX_RETRIES: 3,
    ENABLE_LOGGING: false
  },
  field_specs: [
    { name: "USE_GLOBAL_MODE", label: "全局模式", kind: "bool", section: "常用" },
    { name: "GLOBAL_TOP_N", label: "全局 TopN", kind: "int", section: "常用" },
    { name: "PER_COUNTRY_TOP_N", label: "分国家 TopN", kind: "int", section: "常用" },
    { name: "BANDWIDTH_CANDIDATES", label: "带宽候选数", kind: "int", section: "常用" },
    { name: "OUTPUT_NODE_LIMIT", label: "输出节点上限", kind: "int", section: "常用" },
    { name: "MIN_SUCCESS_RATE", label: "TCP 最低成功率", kind: "float", section: "常用" },
    { name: "TIMEOUT", label: "TCP 超时", kind: "float", section: "常用" },
    { name: "TCP_PROBES", label: "TCP 探测次数", kind: "int", section: "常用" },
    { name: "ENABLE_CF_OFFICIAL_IP_SAMPLING", label: "启用官方 IP 采样", kind: "bool", section: "源池" },
    { name: "CF_OFFICIAL_SAMPLE_PER_24", label: "每个 /24 采样数", kind: "int", section: "源池" },
    { name: "CF_OFFICIAL_SAMPLE_PORTS", label: "官方采样端口", kind: "csv_int", section: "源池" },
    { name: "LOCAL_SEED_FILES", label: "本地种子文件", kind: "csv_str", section: "源池" },
    { name: "ALLOWED_COUNTRIES", label: "允许国家", kind: "csv_str", section: "源池" },
    { name: "OUTPUT_FILE", label: "输出文件", kind: "str", section: "同步" },
    { name: "BACKUP_OUTPUT_ENABLED", label: "启用输出备份", kind: "bool", section: "同步" },
    { name: "OUTPUT_BACKUP_DIR", label: "输出备份目录", kind: "str", section: "同步" },
    { name: "OUTPUT_BACKUP_KEEP", label: "备份保留份数", kind: "int", section: "同步" },
    { name: "GITHUB_SYNC_ENABLED", label: "自动同步 GitHub", kind: "bool", section: "同步" },
    { name: "GITHUB_SYNC_PROXY_URL", label: "GitHub 同步代理", kind: "str", section: "同步" }
  ],
  field_groups: {
    常用: ["USE_GLOBAL_MODE", "GLOBAL_TOP_N", "PER_COUNTRY_TOP_N", "BANDWIDTH_CANDIDATES", "OUTPUT_NODE_LIMIT", "MIN_SUCCESS_RATE", "TIMEOUT", "TCP_PROBES"],
    源池: ["ENABLE_CF_OFFICIAL_IP_SAMPLING", "CF_OFFICIAL_SAMPLE_PER_24", "CF_OFFICIAL_SAMPLE_PORTS", "LOCAL_SEED_FILES", "ALLOWED_COUNTRIES"],
    同步: ["OUTPUT_FILE", "BACKUP_OUTPUT_ENABLED", "OUTPUT_BACKUP_DIR", "OUTPUT_BACKUP_KEEP", "GITHUB_SYNC_ENABLED", "GITHUB_SYNC_PROXY_URL"],
    高级: []
  },
  output_path: "ip.txt",
  output_exists: true,
  output_updated_at: "2026-05-20 19:33:00",
  output_count: 19,
  output_preview: [
    "43.168.16.112:443#HK",
    "154.31.117.200:443#JP",
    "103.117.102.48:443#JP",
    "8.210.29.68:443#HK",
    "219.76.13.169:443#HK"
  ],
  port_share: "68%",
  backups: [
    {
      name: "ip.txt.20260521-030803.bak",
      path: "backups/ip.txt.20260521-030803.bak",
      modified_at: "2026-05-21T03:08:03",
      size: 412
    },
    {
      name: "ip.txt.20260520-193300.bak",
      path: "backups/ip.txt.20260520-193300.bak",
      modified_at: "2026-05-20T19:33:00",
      size: 412
    },
    {
      name: "ip.txt.20260519-221400.bak",
      path: "backups/ip.txt.20260519-221400.bak",
      modified_at: "2026-05-19T22:14:00",
      size: 401
    }
  ],
  preflight: {
    text: "运行模式：工作台检查\n检查结果\n[OK] 配置文件存在：config.json\n[OK] Python 可用\n[OK] 输出目录存在\n[WARN] 优选前请断开 VPN",
    can_continue: true,
    has_warnings: true
  },
  cards: [
    {
      title: "VPN/代理",
      icon: "VPN",
      value: "请断开 VPN",
      detail: "测速阶段保持本地直连",
      accent: "red"
    },
    {
      title: "当前 ip.txt",
      icon: "IP",
      value: "19",
      detail: "2026-05-20 19:33:00",
      accent: "blue"
    },
    {
      title: "GitHub",
      icon: "GH",
      value: "代理未配置",
      detail: "上传阶段可单独走代理",
      accent: "green"
    }
  ]
};

export function isDesktopRuntime() {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

async function runJsonCommand(program: string, args: string[], env?: Record<string, string>) {
  const command = Command.create(program, args, {
    cwd: ".",
    env
  });
  const output = await command.execute();
  const stdout = output.stdout.trim();
  if (!stdout) {
    throw new Error("command returned no output");
  }
  return JSON.parse(stdout) as unknown;
}

function mergeFallback<T extends object>(value: Partial<T> | undefined | null, fallback: T): T {
  if (!value || typeof value !== "object") {
    return fallback;
  }
  return { ...fallback, ...value } as T;
}

export async function loadDesktopState(pythonPath = "python"): Promise<DesktopState> {
  if (!isDesktopRuntime()) {
    return fallbackState;
  }

  try {
    const result = await runJsonCommand(pythonPath, ["-u", BRIDGE_SCRIPT, "state"]);
    return mergeFallback(result as Partial<DesktopState>, fallbackState);
  } catch {
    return fallbackState;
  }
}

export async function saveDesktopConfig(payload: SaveConfigPayload, pythonPath = "python") {
  if (!isDesktopRuntime()) {
    return { saved: payload.mode === "raw" ? payload.config ?? {} : payload.values ?? {} };
  }

  const env = {
    CFNB_UI_PAYLOAD: JSON.stringify(payload)
  };
  return runJsonCommand(pythonPath, ["-u", BRIDGE_SCRIPT, "save-config", "--mode", payload.mode], env) as Promise<SaveResult>;
}

export async function restoreOutputBackup(backupPath: string, pythonPath = "python") {
  if (!isDesktopRuntime()) {
    return { restored_path: backupPath } as RestoreResult;
  }
  return runJsonCommand(pythonPath, ["-u", BRIDGE_SCRIPT, "restore-backup", backupPath]) as Promise<RestoreResult>;
}

export async function openOutputFolder(folderPath: string) {
  if (!isDesktopRuntime()) {
    return;
  }
  await open(folderPath);
}

export function cloneFallbackState() {
  return JSON.parse(JSON.stringify(fallbackState)) as DesktopState;
}
