from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping

DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("config.json")
MAIN_SCRIPT_PATH = Path(__file__).resolve().with_name("main.py")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str
    section: str


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    short_label: str


@dataclass(frozen=True)
class ToolbarAction:
    key: str
    label: str
    variant: str


@dataclass(frozen=True)
class StatusCard:
    title: str
    icon: str
    value: str
    detail: str
    accent: str


@dataclass(frozen=True)
class PreflightReport:
    text: str
    can_continue: bool
    has_warnings: bool


NAV_ITEMS: List[NavItem] = [
    NavItem("workbench", "工作台", "Run"),
    NavItem("results", "结果", "IP"),
    NavItem("settings", "设置", "Set"),
    NavItem("logs", "日志/帮助", "Log"),
]

APP_TOOLBAR_ACTIONS: List[ToolbarAction] = [
    ToolbarAction("refresh_dashboard", "刷新检查", "ghost"),
    ToolbarAction("save_config", "保存配置", "secondary"),
    ToolbarAction("open_output_folder", "输出目录", "soft"),
]

SETTINGS_FIELD_GROUPS: Dict[str, List[str]] = {
    "常用": [
        "USE_GLOBAL_MODE",
        "GLOBAL_TOP_N",
        "PER_COUNTRY_TOP_N",
        "BANDWIDTH_CANDIDATES",
        "OUTPUT_NODE_LIMIT",
        "MIN_SUCCESS_RATE",
        "TIMEOUT",
        "TCP_PROBES",
        "BANDWIDTH_SIZE_MB",
        "TEST_AVAILABILITY",
        "STABILITY_SCORING_ENABLED",
        "FILTER_COUNTRIES_ENABLED",
    ],
    "源池": [
        "ENABLE_CF_OFFICIAL_IP_SAMPLING",
        "CF_OFFICIAL_SAMPLE_PER_24",
        "CF_OFFICIAL_SAMPLE_PORTS",
        "LOCAL_SEED_FILES",
        "ALLOWED_COUNTRIES",
        "FILTER_BLOCKED_COUNTRIES_ENABLED",
        "BLOCKED_COUNTRIES",
    ],
    "同步": [
        "OUTPUT_FILE",
        "BACKUP_OUTPUT_ENABLED",
        "OUTPUT_BACKUP_DIR",
        "OUTPUT_BACKUP_KEEP",
        "STABILITY_STATS_FILE",
        "LOG_FILE",
        "CF_ENABLED",
        "DNS_UPDATE_TARGET_COUNT",
        "ENABLE_WXPUSHER",
        "GITHUB_SYNC_ENABLED",
        "GITHUB_SYNC_PROXY_URL",
        "GITHUB_SYNC_MAX_RETRIES",
        "ENABLE_LOGGING",
    ],
    "高级": [
        "MAX_WORKERS",
        "AVAILABILITY_WORKERS",
        "BANDWIDTH_WORKERS",
        "AVAILABILITY_RETRY_MAX",
        "BANDWIDTH_RETRY_MAX",
        "CF_OFFICIAL_COUNTRY_CODE",
        "CF_DNS_RECORD_NAME",
    ],
}

FIELD_SPECS: List[FieldSpec] = [
    FieldSpec("USE_GLOBAL_MODE", "全局模式", "bool", "常用"),
    FieldSpec("GLOBAL_TOP_N", "全局 TopN", "int", "常用"),
    FieldSpec("PER_COUNTRY_TOP_N", "分国家 TopN", "int", "常用"),
    FieldSpec("BANDWIDTH_CANDIDATES", "带宽候选数", "int", "常用"),
    FieldSpec("OUTPUT_NODE_LIMIT", "输出节点上限", "int", "常用"),
    FieldSpec("MIN_SUCCESS_RATE", "TCP 最低成功率", "float", "常用"),
    FieldSpec("TIMEOUT", "TCP 超时", "float", "常用"),
    FieldSpec("TCP_PROBES", "TCP 探测次数", "int", "常用"),
    FieldSpec("BANDWIDTH_SIZE_MB", "测速大小 MB", "float", "常用"),
    FieldSpec("TEST_AVAILABILITY", "启用可用性检测", "bool", "常用"),
    FieldSpec("STABILITY_SCORING_ENABLED", "启用稳定性评分", "bool", "常用"),
    FieldSpec("FILTER_COUNTRIES_ENABLED", "启用国家过滤", "bool", "常用"),
    FieldSpec("ENABLE_CF_OFFICIAL_IP_SAMPLING", "启用官方 IP 采样", "bool", "源池"),
    FieldSpec("CF_OFFICIAL_SAMPLE_PER_24", "每个 /24 采样数", "int", "源池"),
    FieldSpec("CF_OFFICIAL_SAMPLE_PORTS", "官方采样端口", "csv_int", "源池"),
    FieldSpec("LOCAL_SEED_FILES", "本地种子文件", "csv_str", "源池"),
    FieldSpec("ALLOWED_COUNTRIES", "允许国家", "csv_str", "源池"),
    FieldSpec("FILTER_BLOCKED_COUNTRIES_ENABLED", "屏蔽国家过滤", "bool", "源池"),
    FieldSpec("BLOCKED_COUNTRIES", "屏蔽国家列表", "csv_str", "源池"),
    FieldSpec("OUTPUT_FILE", "输出文件", "str", "同步"),
    FieldSpec("BACKUP_OUTPUT_ENABLED", "启用输出备份", "bool", "同步"),
    FieldSpec("OUTPUT_BACKUP_DIR", "输出备份目录", "str", "同步"),
    FieldSpec("OUTPUT_BACKUP_KEEP", "备份保留份数", "int", "同步"),
    FieldSpec("STABILITY_STATS_FILE", "稳定性统计文件", "str", "同步"),
    FieldSpec("LOG_FILE", "日志文件", "str", "同步"),
    FieldSpec("CF_ENABLED", "启用 Cloudflare DNS", "bool", "同步"),
    FieldSpec("DNS_UPDATE_TARGET_COUNT", "DNS 更新数量", "int", "同步"),
    FieldSpec("ENABLE_WXPUSHER", "启用 WxPusher", "bool", "同步"),
    FieldSpec("GITHUB_SYNC_ENABLED", "自动同步 GitHub", "bool", "同步"),
    FieldSpec("GITHUB_SYNC_PROXY_URL", "GitHub 同步代理", "str", "同步"),
    FieldSpec("GITHUB_SYNC_MAX_RETRIES", "GitHub 重试次数", "int", "同步"),
    FieldSpec("ENABLE_LOGGING", "启用运行日志", "bool", "同步"),
    FieldSpec("MAX_WORKERS", "TCP 并发线程", "int", "高级"),
    FieldSpec("AVAILABILITY_WORKERS", "可用性线程", "int", "高级"),
    FieldSpec("BANDWIDTH_WORKERS", "带宽线程", "int", "高级"),
    FieldSpec("AVAILABILITY_RETRY_MAX", "可用性重试", "int", "高级"),
    FieldSpec("BANDWIDTH_RETRY_MAX", "带宽重试", "int", "高级"),
    FieldSpec("CF_OFFICIAL_COUNTRY_CODE", "官方采样国家码", "str", "高级"),
    FieldSpec("CF_DNS_RECORD_NAME", "Cloudflare 记录名", "str", "高级"),
]

FIELD_SPEC_BY_NAME = {spec.name: spec for spec in FIELD_SPECS}

COLORS = {
    "bg": "#edf6fb",
    "sidebar": "#f8fbff",
    "panel": "#f7fbff",
    "soft_panel": "#f4f8fc",
    "card": "#ffffff",
    "border": "#d5dfec",
    "text": "#0f172a",
    "muted": "#64748b",
    "blue": "#2563eb",
    "blue_dark": "#1d4ed8",
    "blue_soft": "#dbeafe",
    "teal": "#0f766e",
    "teal_soft": "#ccfbf1",
    "green": "#16a34a",
    "red": "#dc2626",
    "input": "#eef2f7",
}

BUTTON_VARIANTS = {
    "primary": {
        "bg": COLORS["blue"],
        "fg": "#ffffff",
        "activebackground": COLORS["blue_dark"],
        "activeforeground": "#ffffff",
        "border": COLORS["blue"],
    },
    "secondary": {
        "bg": COLORS["card"],
        "fg": COLORS["text"],
        "activebackground": COLORS["blue_soft"],
        "activeforeground": COLORS["text"],
        "border": COLORS["border"],
    },
    "soft": {
        "bg": COLORS["blue_soft"],
        "fg": COLORS["blue_dark"],
        "activebackground": "#bfdbfe",
        "activeforeground": COLORS["blue_dark"],
        "border": "#bfdbfe",
    },
    "danger": {
        "bg": COLORS["red"],
        "fg": "#ffffff",
        "activebackground": "#b91c1c",
        "activeforeground": "#ffffff",
        "border": COLORS["red"],
    },
    "ghost": {
        "bg": "#f8fbff",
        "fg": COLORS["muted"],
        "activebackground": COLORS["blue_soft"],
        "activeforeground": COLORS["blue_dark"],
        "border": "#f8fbff",
    },
}


def load_config_file(path: Path | str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config_file(config: Mapping[str, Any], path: Path | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(config), f, ensure_ascii=False, indent=4)
        f.write("\n")


def build_run_command(python_exe: str, main_script: str) -> List[str]:
    return [python_exe, "-u", main_script]


def build_optimize_command(python_exe: str, main_script: str, sync_after: bool) -> List[str]:
    command = build_run_command(python_exe, main_script)
    if not sync_after:
        command.append("--no-github-sync")
    return command


def build_sync_only_command(python_exe: str, main_script: str) -> List[str]:
    return build_run_command(python_exe, main_script) + ["--sync-only"]


PROXY_TEST_CODE = """
import sys
import urllib.request

proxy_url = sys.argv[1] if len(sys.argv) > 1 else ""
handlers = []
if proxy_url:
    handlers.append(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))
opener = urllib.request.build_opener(*handlers)
request = urllib.request.Request("https://github.com/", headers={"User-Agent": "cfnb-desktop-tool"})
response = opener.open(request, timeout=10)
print(f"GitHub proxy test OK: HTTP {getattr(response, 'status', response.getcode())}")
""".strip()


def build_proxy_test_command(python_exe: str, proxy_url: str) -> List[str]:
    return [python_exe, "-c", PROXY_TEST_CODE, proxy_url or ""]


def _is_executable_available(python_exe: str) -> bool:
    if not python_exe:
        return False
    expanded = Path(python_exe).expanduser()
    return expanded.exists() or shutil.which(python_exe) is not None


def _resolve_config_relative(config_path: Path, value: str) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path
    return config_path.expanduser().parent / path


def resolve_output_path(config_path: Path | str, config: Mapping[str, Any]) -> Path:
    return _resolve_config_relative(Path(config_path), str(config.get("OUTPUT_FILE", "ip.txt")))


def resolve_backup_dir(config_path: Path | str, config: Mapping[str, Any]) -> Path:
    return _resolve_config_relative(Path(config_path), str(config.get("OUTPUT_BACKUP_DIR", "backups")))


def read_output_lines(config_path: Path | str, config: Mapping[str, Any]) -> List[str]:
    output_path = resolve_output_path(config_path, config)
    if not output_path.exists():
        return []
    return [line.strip() for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def calculate_port_share(lines: Iterable[str], port: int | str = 443) -> str:
    items = [line.strip() for line in lines if line.strip()]
    if not items:
        return "0%"
    target = str(port)
    matched = 0
    for item in items:
        endpoint = item.split("#", 1)[0]
        if endpoint.rsplit(":", 1)[-1] == target:
            matched += 1
    return f"{round((matched / len(items)) * 100):.0f}%"


def build_workbench_status_cards(
    config_path: Path | str,
    config: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
) -> List[StatusCard]:
    environ = os.environ if environ is None else environ
    proxy_env_keys = [
        key for key, value in environ.items()
        if key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"} and value
    ]
    if proxy_env_keys:
        vpn_card = StatusCard(
            "VPN/代理提醒",
            "VPN",
            "检测到代理变量",
            "优选前请确认测速不走代理",
            COLORS["red"],
        )
    else:
        vpn_card = StatusCard(
            "VPN/代理提醒",
            "VPN",
            "请断开 VPN",
            "测速阶段保持本地直连",
            COLORS["red"],
        )

    try:
        output_lines = read_output_lines(config_path, config)
        count = str(len(output_lines))
        share = calculate_port_share(output_lines)
    except Exception:
        count = "0"
        share = "读取失败"

    output_card = StatusCard(
        "当前 ip.txt",
        "IP",
        count,
        share,
        COLORS["blue_dark"],
    )

    proxy_url = str(config.get("GITHUB_SYNC_PROXY_URL", "")).strip()
    github_card = StatusCard(
        "GitHub 上传",
        "GH",
        "代理已配置" if proxy_url else "代理未配置",
        proxy_url or "上传阶段可单独走代理",
        COLORS["green"] if proxy_url else COLORS["muted"],
    )

    return [vpn_card, output_card, github_card]


def list_output_backups(config_path: Path | str, config: Mapping[str, Any]) -> List[Path]:
    output_path = resolve_output_path(config_path, config)
    backup_dir = resolve_backup_dir(config_path, config)
    if not backup_dir.exists():
        return []
    pattern = f"{output_path.name}.*.bak"
    return sorted(
        backup_dir.glob(pattern),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )


def _prune_backups(backup_dir: Path, output_path: Path, keep: int) -> None:
    if keep <= 0 or not backup_dir.exists():
        return
    backups = sorted(
        backup_dir.glob(f"{output_path.name}.*.bak"),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    for stale_path in backups[keep:]:
        try:
            stale_path.unlink()
        except OSError:
            pass


def backup_current_output_file(output_path: Path, backup_dir: Path, keep: int) -> Path | None:
    if not output_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{output_path.name}.{timestamp}.bak"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"{output_path.name}.{timestamp}-{counter}.bak"
        counter += 1
    shutil.copy2(output_path, backup_path)
    _prune_backups(backup_dir, output_path, keep)
    return backup_path


def restore_output_backup(
    backup_path: Path | str,
    config_path: Path | str,
    config: Mapping[str, Any],
    backup_callback: Callable[[Path, Path, int], Path | None] = backup_current_output_file,
) -> Path:
    selected_backup = Path(backup_path)
    if not selected_backup.exists():
        raise FileNotFoundError(selected_backup)
    output_path = resolve_output_path(config_path, config)
    backup_dir = resolve_backup_dir(config_path, config)
    keep = int(config.get("OUTPUT_BACKUP_KEEP", 20) or 20)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    backup_callback(output_path, backup_dir, keep)
    shutil.copy2(selected_backup, output_path)
    return output_path


def format_backup_label(path: Path) -> str:
    size = path.stat().st_size
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))
    return f"{stamp}  {path.name}  {size} B"


def build_restore_confirmation_message(backup_path: Path | str) -> str:
    path = Path(backup_path)
    return (
        "将用此备份覆盖当前 ip.txt：\n"
        f"{path.name}\n\n"
        "恢复前会先备份当前 ip.txt。继续？"
    )


def build_preflight_report(
    config_path: Path,
    config: Mapping[str, Any],
    python_exe: str,
    mode_label: str,
    sync_requested: bool | None = None,
    environ: Mapping[str, str] | None = None,
) -> PreflightReport:
    environ = os.environ if environ is None else environ
    config_path = Path(config_path).expanduser()
    errors: List[str] = []
    warnings: List[str] = ["请确认优选前已断开 VPN，测速阶段应保持本地直连。"]
    ok: List[str] = []

    if config_path.exists():
        ok.append(f"配置文件存在: {config_path}")
    else:
        errors.append(f"配置文件不存在: {config_path}")

    if _is_executable_available(python_exe):
        ok.append(f"Python 可用: {python_exe}")
    else:
        errors.append(f"Python 不可用: {python_exe}")

    output_file = resolve_output_path(config_path, config)
    if output_file.parent.exists():
        ok.append(f"输出目录存在: {output_file.parent}")
    else:
        warnings.append(f"输出目录当前不存在，运行时可能无法写入: {output_file.parent}")

    if sync_requested is None:
        sync_requested = "GitHub" in mode_label or "上传" in mode_label or bool(config.get("GITHUB_SYNC_ENABLED"))
    if sync_requested:
        script_name = "git_sync.ps1" if sys.platform == "win32" else "git_sync.sh"
        script_path = MAIN_SCRIPT_PATH.parent / script_name
        if script_path.exists():
            ok.append(f"上传脚本存在: {script_name}")
        else:
            warnings.append(f"上传脚本不存在，GitHub 同步会跳过: {script_name}")

    proxy_url = str(config.get("GITHUB_SYNC_PROXY_URL", "")).strip()
    if proxy_url:
        ok.append(f"GitHub 同步代理已填写: {proxy_url}")
    elif sync_requested:
        warnings.append("GitHub 同步代理为空；如果当前网络无法访问 GitHub，请先填写代理。")

    proxy_env_keys = [
        key for key, value in environ.items()
        if key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"} and value
    ]
    if proxy_env_keys:
        warnings.append("检测到环境代理变量，优选前请确认它不会影响测速: " + ", ".join(sorted(proxy_env_keys)))

    lines = [f"运行模式: {mode_label}", "", "检查结果"]
    lines.extend(f"[OK] {item}" for item in ok)
    lines.extend(f"[WARN] {item}" for item in warnings)
    lines.extend(f"[ERROR] {item}" for item in errors)

    return PreflightReport(
        text="\n".join(lines),
        can_continue=not errors,
        has_warnings=bool(warnings),
    )


def _split_csv_text(value: str) -> List[str]:
    parts = []
    for chunk in value.replace("\n", ",").replace(";", ",").split(","):
        item = chunk.strip()
        if item:
            parts.append(item)
    return parts


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "是", "启用"}


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    return int(text)


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    return float(text)


def _format_csv(values: Iterable[Any]) -> str:
    return ", ".join(str(item) for item in values if str(item).strip())


def _coerce_csv_int(value: Any) -> List[int]:
    if isinstance(value, list):
        return [_coerce_int(item) for item in value if str(item).strip() != ""]
    return [_coerce_int(item) for item in _split_csv_text(str(value))]


def _coerce_csv_str(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _split_csv_text(str(value))


def extract_common_field_values(config: Mapping[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for spec in FIELD_SPECS:
        raw = config.get(spec.name)
        if spec.kind == "bool":
            values[spec.name] = _coerce_bool(raw)
        elif spec.kind == "int":
            values[spec.name] = "" if raw is None else str(_coerce_int(raw))
        elif spec.kind == "float":
            values[spec.name] = "" if raw is None else str(_coerce_float(raw))
        elif spec.kind == "csv_int":
            values[spec.name] = _format_csv(_coerce_csv_int(raw or []))
        elif spec.kind == "csv_str":
            values[spec.name] = _format_csv(_coerce_csv_str(raw or []))
        else:
            values[spec.name] = "" if raw is None else str(raw)
    return values


def apply_common_field_values(config: Mapping[str, Any], values: Mapping[str, Any]) -> Dict[str, Any]:
    updated = dict(config)
    for spec in FIELD_SPECS:
        if spec.name not in values:
            continue
        raw = values[spec.name]
        if spec.kind == "bool":
            updated[spec.name] = _coerce_bool(raw)
        elif spec.kind == "int":
            updated[spec.name] = _coerce_int(raw)
        elif spec.kind == "float":
            updated[spec.name] = _coerce_float(raw)
        elif spec.kind == "csv_int":
            updated[spec.name] = _coerce_csv_int(raw)
        elif spec.kind == "csv_str":
            updated[spec.name] = _coerce_csv_str(raw)
        else:
            updated[spec.name] = str(raw).strip()
    return updated


def split_setting_fields_for_columns(field_names: List[str], columns: int = 2) -> List[List[str]]:
    column_count = max(1, columns)
    grouped: List[List[str]] = [[] for _ in range(column_count)]
    for index, name in enumerate(field_names):
        grouped[index % column_count].append(name)
    return grouped


def format_config_text(config: Mapping[str, Any]) -> str:
    return json.dumps(dict(config), ensure_ascii=False, indent=2)


def parse_config_text(text: str) -> Dict[str, Any]:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


class ProcessRunner:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._wait_thread: threading.Thread | None = None

    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, python_exe: str, config_path: Path) -> None:
        command = build_run_command(python_exe, str(MAIN_SCRIPT_PATH))
        self.start_command(command, cwd=MAIN_SCRIPT_PATH.parent)

    def start_command(
        self,
        command: List[str],
        cwd: Path | str | None = None,
        env_overrides: Mapping[str, str] | None = None,
    ) -> None:
        if self.running():
            raise RuntimeError("process already running")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        if env_overrides:
            env.update(dict(env_overrides))
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd or MAIN_SCRIPT_PATH.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        self.queue.put(("status", f"已启动: {' '.join(command)}"))
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()
        self._wait_thread = threading.Thread(target=self._wait_for_exit, daemon=True)
        self._wait_thread.start()

    def _read_stdout(self) -> None:
        assert self.process is not None
        stream = self.process.stdout
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            self.queue.put(("log", line.rstrip("\n")))
        stream.close()

    def _wait_for_exit(self) -> None:
        assert self.process is not None
        code = self.process.wait()
        self.queue.put(("exit", code))

    def stop(self) -> None:
        if not self.running():
            return
        assert self.process is not None
        self.process.terminate()


class DesktopApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, ttk

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.scrolledtext = scrolledtext
        self.ttk = ttk

        self.root = tk.Tk()
        self.root.title("cfnb 手动优选工具")
        self.root.geometry("1280x860")
        self.root.minsize(1120, 740)
        self.root.configure(bg=COLORS["bg"])

        self.runner = ProcessRunner()
        self.config_path_var = tk.StringVar(value=str(DEFAULT_CONFIG_PATH))
        self.status_var = tk.StringVar(value="准备就绪")
        self.page_title_var = tk.StringVar(value="工作台")
        self.python_var = tk.StringVar(value=sys.executable)
        self.result_count_var = tk.StringVar(value="0")
        self.port_share_var = tk.StringVar(value="0%")
        self.output_updated_var = tk.StringVar(value="未生成")
        self.github_status_var = tk.StringVar(value="未检查")
        self.vpn_status_var = tk.StringVar(value="请断开 VPN 后优选")
        self.vpn_detail_var = tk.StringVar(value="测速阶段保持本地直连")
        self.result_detail_var = tk.StringVar(value="443 占比 0%")
        self.github_detail_var = tk.StringVar(value="上传阶段可单独走代理")
        self.backup_count_var = tk.StringVar(value="0")
        self.output_file_var = tk.StringVar(value="")
        self.status_accent_vars: Dict[str, Any] = {}

        self.config_data: Dict[str, Any] = {}
        self.form_vars: Dict[str, Any] = {}
        self.page_frames: Dict[str, Any] = {}
        self.nav_buttons: Dict[str, Any] = {}
        self.toolbar_buttons: Dict[str, Any] = {}
        self.settings_frames: Dict[str, Any] = {}
        self.settings_buttons: Dict[str, Any] = {}
        self.active_page = "workbench"
        self.active_settings_group = "常用"
        self.backup_paths: List[Path] = []
        self.log_lines: List[str] = []

        self.raw_text = None
        self.log_text = None
        self.dashboard_log_text = None
        self.result_list = None
        self.result_preview_list = None
        self.backup_list = None
        self.preflight_text = None

        self._configure_styles()
        self._build_ui()
        self._load_from_disk()
        self._poll_runner_queue()

    def _configure_styles(self) -> None:
        style = self.ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass
        style.configure("App.TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("Muted.TLabel", background=COLORS["card"], foreground=COLORS["muted"])
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["blue_dark"], font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold"))

    def _build_ui(self) -> None:
        tk = self.tk

        shell = tk.Frame(self.root, bg=COLORS["bg"])
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(shell, bg=COLORS["sidebar"], width=96, highlightbackground=COLORS["border"], highlightthickness=1)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        tk.Label(sidebar, text="cfnb", bg=COLORS["sidebar"], fg=COLORS["blue_dark"], font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(24, 18))
        for item in NAV_ITEMS:
            button = tk.Button(
                sidebar,
                text=f"{item.short_label}\n{item.label}",
                command=lambda key=item.key: self._show_page(key),
                relief="flat",
                bd=0,
                width=9,
                height=3,
                font=("Microsoft YaHei UI", 8, "bold"),
                cursor="hand2",
            )
            button.pack(padx=12, pady=6)
            self.nav_buttons[item.key] = button

        tk.Label(sidebar, text="手动", bg=COLORS["sidebar"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="bottom", pady=(0, 18))

        main = tk.Frame(shell, bg=COLORS["bg"])
        main.grid(row=0, column=1, sticky="nsew", padx=26, pady=22)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = tk.Frame(main, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        title_stack = tk.Frame(header, bg=COLORS["bg"])
        title_stack.grid(row=0, column=0, sticky="w")
        tk.Label(title_stack, textvariable=self.page_title_var, bg=COLORS["bg"], fg=COLORS["blue_dark"], font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w")
        tk.Label(title_stack, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 10)).pack(anchor="w", pady=(4, 0))

        toolbar = tk.Frame(header, bg=COLORS["bg"])
        toolbar.grid(row=0, column=1, sticky="e")
        for action in APP_TOOLBAR_ACTIONS:
            button = self._primary_button(
                toolbar,
                action.label,
                lambda key=action.key: self._run_toolbar_action(key),
                variant=action.variant,
            )
            button.pack(side="left", padx=(8, 0))
            self.toolbar_buttons[action.key] = button

        self.content_host = tk.Frame(main, bg=COLORS["bg"])
        self.content_host.grid(row=1, column=0, sticky="nsew")
        self.content_host.grid_rowconfigure(0, weight=1)
        self.content_host.grid_columnconfigure(0, weight=1)

        self._build_workbench_page()
        self._build_results_page()
        self._build_settings_page()
        self._build_logs_page()
        self._show_page("workbench")

    def _card(self, parent: Any, title: str | None = None, subtitle: str | None = None, padding: int = 14) -> Any:
        frame = self.tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        if title:
            self.tk.Label(frame, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=padding, pady=(padding, 4))
        if subtitle:
            self.tk.Label(frame, text=subtitle, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=padding, pady=(0, 4))
        return frame

    def _metric_card(
        self,
        parent: Any,
        title: str,
        variable: Any,
        accent: str = COLORS["text"],
        detail_variable: Any | None = None,
        icon: str = "",
    ) -> Any:
        frame = self._card(parent)
        body = self.tk.Frame(frame, bg=COLORS["card"])
        body.pack(fill="x", padx=14, pady=14)
        body.grid_columnconfigure(1, weight=1)

        icon_label = self.tk.Label(
            body,
            text=icon or title[:2],
            bg=accent,
            fg="#ffffff",
            width=5,
            height=2,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        icon_label.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))

        text_stack = self.tk.Frame(body, bg=COLORS["card"])
        text_stack.grid(row=0, column=1, sticky="ew")
        self.tk.Label(text_stack, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        value_label = self.tk.Label(text_stack, textvariable=variable, bg=COLORS["card"], fg=accent, font=("Microsoft YaHei UI", 22, "bold"))
        value_label.pack(anchor="w", pady=(2, 0))
        if detail_variable is not None:
            self.tk.Label(text_stack, textvariable=detail_variable, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(0, 0))
        frame.value_label = value_label
        return frame

    def _primary_button(
        self,
        parent: Any,
        text: str,
        command: Callable[[], None],
        primary: bool = False,
        variant: str | None = None,
    ) -> Any:
        chosen_variant = variant or ("primary" if primary else "secondary")
        style = BUTTON_VARIANTS[chosen_variant]
        return self.tk.Button(
            parent,
            text=text,
            command=command,
            bg=style["bg"],
            fg=style["fg"],
            activebackground=style["activebackground"],
            activeforeground=style["activeforeground"],
            relief="flat",
            bd=0,
            highlightbackground=style["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )

    def _build_workbench_page(self) -> None:
        page = self.tk.Frame(self.content_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(1, weight=1)
        self.page_frames["workbench"] = page

        metrics = self.tk.Frame(page, bg=COLORS["bg"])
        metrics.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        for col in range(3):
            metrics.grid_columnconfigure(col, weight=1, uniform="metrics")
        vpn_card = self._metric_card(metrics, "VPN/代理提醒", self.vpn_status_var, COLORS["red"], self.vpn_detail_var, icon="VPN")
        vpn_card.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.status_accent_vars["vpn"] = vpn_card.value_label
        result_card = self._metric_card(metrics, "当前 ip.txt", self.result_count_var, COLORS["blue_dark"], self.result_detail_var, icon="IP")
        result_card.grid(row=0, column=1, sticky="ew", padx=6)
        self.status_accent_vars["result"] = result_card.value_label
        github_card = self._metric_card(metrics, "GitHub 上传", self.github_status_var, COLORS["green"], self.github_detail_var, icon="GH")
        github_card.grid(row=0, column=2, sticky="ew", padx=(12, 0))
        self.status_accent_vars["github"] = github_card.value_label

        left = self.tk.Frame(page, bg=COLORS["bg"])
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        action_card = self._card(left, "手动操作", "优选阶段建议断开 VPN；上传阶段可单独走代理。")
        action_card.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        actions = self.tk.Frame(action_card, bg=COLORS["card"])
        actions.pack(fill="x", padx=14, pady=(8, 14))
        for col in range(4):
            actions.grid_columnconfigure(col, weight=1, uniform="actions")
        self._primary_button(actions, "只运行优选", lambda: self._start_optimize(sync_after=False), primary=True).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._primary_button(actions, "优选后自动上传", lambda: self._start_optimize(sync_after=True), variant="soft").grid(row=0, column=1, sticky="ew", padx=4)
        self._primary_button(actions, "上传到 GitHub", self._start_sync_only).grid(row=0, column=2, sticky="ew", padx=4)
        self._primary_button(actions, "测试 GitHub 代理", self._start_proxy_test).grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self._primary_button(actions, "停止当前任务", self.runner.stop, variant="danger").grid(row=1, column=0, sticky="ew", pady=(10, 0), padx=(0, 8))
        self._primary_button(actions, "保存配置", self._save_to_disk, variant="secondary").grid(row=1, column=1, sticky="ew", pady=(10, 0), padx=4)
        self._primary_button(actions, "刷新检查", self._refresh_dashboard, variant="secondary").grid(row=1, column=2, sticky="ew", pady=(10, 0), padx=4)
        self._primary_button(actions, "打开输出目录", self._open_output_folder, variant="secondary").grid(row=1, column=3, sticky="ew", pady=(10, 0), padx=(8, 0))

        preview_card = self._card(left, "最新结果预览", "客户端还会二次优选，这里优先保持 443 输出稳定。")
        preview_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        preview_meta = self.tk.Frame(preview_card, bg=COLORS["card"])
        preview_meta.pack(fill="x", padx=14, pady=(4, 10))
        self.tk.Label(preview_meta, text="443 占比", bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")
        self.tk.Label(preview_meta, textvariable=self.port_share_var, bg=COLORS["card"], fg=COLORS["blue_dark"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=(8, 20))
        self.tk.Label(preview_meta, text="更新时间", bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")
        self.tk.Label(preview_meta, textvariable=self.output_updated_var, bg=COLORS["card"], fg=COLORS["text"]).pack(side="left", padx=(8, 0))
        self.result_preview_list = self.tk.Listbox(preview_card, height=8, relief="flat", bd=0, bg="#f8fbff", fg=COLORS["text"], font=("Consolas", 10))
        self.result_preview_list.pack(fill="x", padx=14, pady=(0, 14))

        log_card = self._card(left, "运行日志")
        log_card.grid(row=2, column=0, sticky="nsew")
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        self.dashboard_log_text = self.scrolledtext.ScrolledText(log_card, wrap="word", height=8, state="disabled", relief="flat", bg="#f8fbff")
        self.dashboard_log_text.pack(fill="both", expand=True, padx=14, pady=(8, 14))

        right = self._card(page, "运行前检查")
        right.grid(row=1, column=1, sticky="nsew")
        self.preflight_text = self.scrolledtext.ScrolledText(right, wrap="word", height=18, state="disabled", relief="flat", bg="#f8fbff")
        self.preflight_text.pack(fill="both", expand=True, padx=14, pady=(8, 14))

    def _build_results_page(self) -> None:
        page = self.tk.Frame(self.content_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(1, weight=1)
        self.page_frames["results"] = page

        summary = self.tk.Frame(page, bg=COLORS["bg"])
        summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        for col in range(3):
            summary.grid_columnconfigure(col, weight=1, uniform="result-metrics")
        self._metric_card(summary, "节点总数", self.result_count_var, COLORS["blue_dark"], icon="IP").grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self._metric_card(summary, "443 占比", self.port_share_var, COLORS["teal"], icon="443").grid(row=0, column=1, sticky="ew", padx=6)
        self._metric_card(summary, "备份数量", self.backup_count_var, COLORS["green"], icon="BAK").grid(row=0, column=2, sticky="ew", padx=(12, 0))

        result_card = self._card(page, "ip.txt", "最终订阅源内容，格式保持 IP:port#CC。")
        result_card.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        self.result_list = self.tk.Listbox(result_card, relief="flat", bd=0, bg="#f8fbff", fg=COLORS["text"], font=("Consolas", 10))
        self.result_list.pack(fill="both", expand=True, padx=14, pady=(8, 12))
        result_buttons = self.tk.Frame(result_card, bg=COLORS["card"])
        result_buttons.pack(fill="x", padx=14, pady=(0, 14))
        self._primary_button(result_buttons, "刷新结果", self._refresh_results, primary=True).pack(side="left")
        self._primary_button(result_buttons, "打开输出目录", self._open_output_folder).pack(side="left", padx=(10, 0))

        backup_card = self._card(page, "历史备份", "恢复会先保护当前 ip.txt，再覆盖为选中版本。")
        backup_card.grid(row=1, column=1, sticky="nsew")
        self.backup_list = self.tk.Listbox(backup_card, relief="flat", bd=0, bg="#f8fbff", fg=COLORS["text"], font=("Microsoft YaHei UI", 9))
        self.backup_list.pack(fill="both", expand=True, padx=14, pady=(8, 12))
        backup_buttons = self.tk.Frame(backup_card, bg=COLORS["card"])
        backup_buttons.pack(fill="x", padx=14, pady=(0, 14))
        self._primary_button(backup_buttons, "恢复选中备份", self._restore_selected_backup, variant="danger").pack(side="left")
        self._primary_button(backup_buttons, "刷新备份", self._refresh_backups).pack(side="left", padx=(10, 0))

    def _build_settings_page(self) -> None:
        page = self.tk.Frame(self.content_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.page_frames["settings"] = page

        top = self._card(page, "配置文件", "日常只改常用项；完整 JSON 保留在高级页兜底。")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        top_inner = self.tk.Frame(top, bg=COLORS["card"])
        top_inner.pack(fill="x", padx=14, pady=(8, 14))
        top_inner.grid_columnconfigure(1, weight=1)
        self.tk.Label(top_inner, text="路径", bg=COLORS["card"], fg=COLORS["muted"]).grid(row=0, column=0, sticky="w")
        self.tk.Entry(top_inner, textvariable=self.config_path_var, relief="flat", bg=COLORS["input"]).grid(row=0, column=1, sticky="ew", padx=10, ipady=6)
        self._primary_button(top_inner, "浏览", self._browse_config).grid(row=0, column=2, padx=(0, 8))
        self._primary_button(top_inner, "加载", self._load_from_disk).grid(row=0, column=3, padx=(0, 8))
        self._primary_button(top_inner, "保存", self._save_to_disk, primary=True).grid(row=0, column=4)
        self.tk.Label(top_inner, text="Python", bg=COLORS["card"], fg=COLORS["muted"]).grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.tk.Entry(top_inner, textvariable=self.python_var, relief="flat", bg=COLORS["input"]).grid(row=1, column=1, columnspan=4, sticky="ew", padx=(10, 0), pady=(10, 0), ipady=6)

        body = self._card(page)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        tabs = self.tk.Frame(body, bg=COLORS["card"])
        tabs.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        for group in SETTINGS_FIELD_GROUPS:
            button = self._primary_button(tabs, group, lambda name=group: self._show_settings_group(name), variant="soft" if group == self.active_settings_group else "secondary")
            button.pack(side="left", padx=(0, 8))
            self.settings_buttons[group] = button

        settings_host = self.tk.Frame(body, bg=COLORS["card"])
        settings_host.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        settings_host.grid_rowconfigure(0, weight=1)
        settings_host.grid_columnconfigure(0, weight=1)
        for group, field_names in SETTINGS_FIELD_GROUPS.items():
            frame = self.tk.Frame(settings_host, bg=COLORS["card"])
            frame.grid(row=0, column=0, sticky="nsew")
            self.settings_frames[group] = frame
            if group == "高级":
                self._build_advanced_settings_group(frame, field_names)
            else:
                self._build_field_group(frame, field_names)
        self._show_settings_group("常用")

    def _build_setting_row(self, parent: Any, spec: FieldSpec) -> Any:
        row = self.tk.Frame(
            parent,
            bg=COLORS["soft_panel"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        row.grid_columnconfigure(0, weight=1)
        label_stack = self.tk.Frame(row, bg=COLORS["soft_panel"])
        label_stack.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        self.tk.Label(label_stack, text=spec.label, bg=COLORS["soft_panel"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        self.tk.Label(label_stack, text=spec.name, bg=COLORS["soft_panel"], fg=COLORS["muted"], font=("Consolas", 8)).pack(anchor="w", pady=(3, 0))

        if spec.kind == "bool":
            var = self.tk.BooleanVar(value=False)
            widget = self.tk.Checkbutton(
                row,
                variable=var,
                bg=COLORS["soft_panel"],
                activebackground=COLORS["soft_panel"],
                relief="flat",
                selectcolor=COLORS["card"],
            )
            widget.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=10)
        else:
            var = self.tk.StringVar(value="")
            widget = self.tk.Entry(
                row,
                textvariable=var,
                relief="flat",
                bg=COLORS["card"],
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                width=24,
            )
            widget.grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=10, ipady=5)
        self.form_vars[spec.name] = var
        return row

    def _build_field_group(self, parent: Any, field_names: List[str]) -> None:
        parent.grid_rowconfigure(0, weight=1)
        columns = split_setting_fields_for_columns(field_names, columns=2)
        for col_index, names in enumerate(columns):
            parent.grid_columnconfigure(col_index, weight=1, uniform="settings-columns")
            column_frame = self.tk.Frame(parent, bg=COLORS["card"])
            column_frame.grid(row=0, column=col_index, sticky="nsew", padx=(0, 8) if col_index == 0 else (8, 0))
            column_frame.grid_columnconfigure(0, weight=1)
            for row_index, name in enumerate(names):
                row = self._build_setting_row(column_frame, FIELD_SPEC_BY_NAME[name])
                row.grid(row=row_index, column=0, sticky="ew", pady=(0, 8))

    def _build_advanced_settings_group(self, parent: Any, field_names: List[str]) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_rowconfigure(0, weight=1)
        advanced_form = self.tk.Frame(parent, bg=COLORS["card"])
        advanced_form.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._build_field_group(advanced_form, field_names)

        raw_frame = self.tk.Frame(parent, bg=COLORS["card"])
        raw_frame.grid(row=0, column=1, sticky="nsew")
        raw_frame.grid_rowconfigure(1, weight=1)
        raw_frame.grid_columnconfigure(0, weight=1)
        bar = self.tk.Frame(raw_frame, bg=COLORS["card"])
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._primary_button(bar, "应用原始 JSON", self._apply_raw_to_form, primary=True).pack(side="left")
        self._primary_button(bar, "从表单刷新 JSON", self._refresh_raw_from_form).pack(side="left", padx=(10, 0))
        self.raw_text = self.scrolledtext.ScrolledText(raw_frame, wrap="none", height=20, undo=True, relief="flat", bg="#f8fbff")
        self.raw_text.grid(row=1, column=0, sticky="nsew")

    def _build_logs_page(self) -> None:
        page = self.tk.Frame(self.content_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=2)
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure(0, weight=1)
        self.page_frames["logs"] = page

        log_card = self._card(page, "完整运行日志")
        log_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.log_text = self.scrolledtext.ScrolledText(log_card, wrap="word", height=20, state="disabled", relief="flat", bg="#f8fbff")
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(8, 14))

        help_card = self._card(page, "手动流程")
        help_card.grid(row=0, column=1, sticky="nsew")
        help_text = (
            "1. 优选前断开 VPN，保证测速走本地直连。\n\n"
            "2. 点击“只运行优选”生成新的 ip.txt。\n\n"
            "3. 需要上传时连接代理或 VPN，再点击“上传到 GitHub”。\n\n"
            "4. 如果结果不理想，到“结果”页选择备份恢复。"
        )
        self.tk.Label(help_card, text=help_text, bg=COLORS["card"], fg=COLORS["text"], justify="left", anchor="nw", font=("Microsoft YaHei UI", 10)).pack(fill="both", expand=True, padx=14, pady=(8, 14))

    def _run_toolbar_action(self, key: str) -> None:
        if key == "refresh_dashboard":
            self._refresh_dashboard()
            return
        if key == "save_config":
            self._save_to_disk()
            return
        if key == "open_output_folder":
            self._open_output_folder()
            return
        raise ValueError(f"unknown toolbar action: {key}")

    def _show_page(self, key: str) -> None:
        self.active_page = key
        for page_key, frame in self.page_frames.items():
            if page_key == key:
                frame.tkraise()
            frame.grid(row=0, column=0, sticky="nsew")
        for item in NAV_ITEMS:
            button = self.nav_buttons[item.key]
            active = item.key == key
            button.configure(
                bg=COLORS["blue"] if active else "#f1f5f9",
                fg="#ffffff" if active else COLORS["text"],
                activebackground=COLORS["blue_dark"] if active else COLORS["blue_soft"],
            )
            if active:
                self.page_title_var.set(item.label)
        if key in {"workbench", "results"}:
            self._refresh_results()
        elif key == "settings":
            self._refresh_raw_from_form()

    def _show_settings_group(self, group: str) -> None:
        self.active_settings_group = group
        for name, frame in self.settings_frames.items():
            if name == group:
                frame.tkraise()
        for name, button in self.settings_buttons.items():
            active = name == group
            style = BUTTON_VARIANTS["soft" if active else "secondary"]
            button.configure(
                bg=style["bg"],
                fg=style["fg"],
                activebackground=style["activebackground"],
                activeforeground=style["activeforeground"],
                highlightbackground=style["border"],
            )

    def _browse_config(self) -> None:
        path = self.filedialog.askopenfilename(
            title="选择 config.json",
            initialdir=str(Path(self.config_path_var.get()).parent),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.config_path_var.set(path)
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        path = Path(self.config_path_var.get()).expanduser()
        try:
            self.config_data = load_config_file(path)
        except Exception as exc:
            self.messagebox.showerror("加载失败", f"无法读取配置文件：{exc}")
            return
        self._sync_config_to_form()
        self.status_var.set(f"已加载配置 {path}")
        self._refresh_raw_from_form()
        self._refresh_dashboard()

    def _save_to_disk(self) -> bool:
        try:
            self._sync_form_to_config()
            save_config_file(self.config_data, Path(self.config_path_var.get()).expanduser())
        except Exception as exc:
            self.messagebox.showerror("保存失败", f"无法保存配置文件：{exc}")
            return False
        self.status_var.set(f"已保存配置 {self.config_path_var.get()}")
        self._refresh_dashboard()
        return True

    def _sync_config_to_form(self) -> None:
        values = extract_common_field_values(self.config_data)
        for name, var in self.form_vars.items():
            value = values.get(name, "")
            if isinstance(var, self.tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(value)

    def _sync_form_to_config(self) -> None:
        current = {}
        for spec in FIELD_SPECS:
            var = self.form_vars.get(spec.name)
            if var is None:
                continue
            current[spec.name] = var.get()
        self.config_data = apply_common_field_values(self.config_data, current)
        self._refresh_raw_from_form()

    def _refresh_raw_from_form(self) -> None:
        if self.raw_text is None:
            return
        self.raw_text.delete("1.0", self.tk.END)
        self.raw_text.insert("1.0", format_config_text(self.config_data))

    def _apply_raw_to_form(self) -> None:
        try:
            text = self.raw_text.get("1.0", self.tk.END)
            self.config_data = parse_config_text(text)
        except Exception as exc:
            self.messagebox.showerror("JSON 错误", f"原始配置无法解析：{exc}")
            return
        self._sync_config_to_form()
        self.status_var.set("已从原始 JSON 应用配置")
        self._refresh_dashboard()

    def _append_to_text_widget(self, widget: Any, line: str) -> None:
        if widget is None:
            return
        widget.configure(state="normal")
        widget.insert(self.tk.END, line + "\n")
        widget.see(self.tk.END)
        widget.configure(state="disabled")

    def _append_log(self, line: str) -> None:
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-500:]
        self._append_to_text_widget(self.log_text, line)
        self._append_to_text_widget(self.dashboard_log_text, line)

    def _clear_text_widget(self, widget: Any) -> None:
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", self.tk.END)
        widget.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_lines.clear()
        self._clear_text_widget(self.log_text)
        self._clear_text_widget(self.dashboard_log_text)

    def _write_preflight_panel(self, report: PreflightReport) -> None:
        if self.preflight_text is None:
            return
        self.preflight_text.configure(state="normal")
        self.preflight_text.delete("1.0", self.tk.END)
        self.preflight_text.insert("1.0", report.text)
        self.preflight_text.configure(state="disabled")

    def _build_current_preflight_report(self, mode_label: str = "工作台检查", sync_after: bool | None = None) -> PreflightReport:
        return build_preflight_report(
            config_path=Path(self.config_path_var.get()).expanduser(),
            config=self.config_data,
            python_exe=self.python_var.get().strip() or sys.executable,
            mode_label=mode_label,
            sync_requested=sync_after,
        )

    def _confirm_preflight(self, mode_label: str, sync_after: bool | None = None) -> bool:
        self._sync_form_to_config()
        report = self._build_current_preflight_report(mode_label, sync_after)
        self._write_preflight_panel(report)
        if not report.can_continue:
            self.messagebox.showerror("运行前检查未通过", report.text)
            return False
        return self.messagebox.askyesno("运行前检查", report.text + "\n\n继续运行？")

    def _start_command(self, command: List[str], status_text: str) -> None:
        if self.runner.running():
            self.messagebox.showinfo("运行中", "当前已有任务在运行。")
            return
        if not self._save_to_disk():
            return
        self._clear_log()
        self._show_page("logs" if "--sync-only" in command else "workbench")
        try:
            self.runner.start_command(command, cwd=MAIN_SCRIPT_PATH.parent)
        except Exception as exc:
            self.messagebox.showerror("启动失败", f"无法启动任务：{exc}")
            return
        self.status_var.set(status_text)

    def _start_optimize(self, sync_after: bool) -> None:
        mode_label = "优选后按设置自动上传" if sync_after else "只运行优选"
        if not self._confirm_preflight(mode_label, sync_after=sync_after):
            return
        command = build_optimize_command(
            self.python_var.get().strip() or sys.executable,
            str(MAIN_SCRIPT_PATH),
            sync_after=sync_after,
        )
        self._start_command(command, "运行中")

    def _start_sync_only(self) -> None:
        if not self._confirm_preflight("上传到 GitHub", sync_after=True):
            return
        command = build_sync_only_command(self.python_var.get().strip() or sys.executable, str(MAIN_SCRIPT_PATH))
        self._start_command(command, "正在上传到 GitHub")

    def _start_proxy_test(self) -> None:
        self._sync_form_to_config()
        proxy_url = str(self.config_data.get("GITHUB_SYNC_PROXY_URL", "")).strip()
        if not proxy_url:
            self.messagebox.showinfo("代理为空", "请先填写 GitHub 同步代理地址。")
            return
        command = build_proxy_test_command(self.python_var.get().strip() or sys.executable, proxy_url)
        self._start_command(command, "正在测试 GitHub 代理")

    def _start_run(self) -> None:
        self._start_optimize(sync_after=True)

    def _save_and_run(self) -> None:
        self._start_optimize(sync_after=True)

    def _poll_runner_queue(self) -> None:
        while True:
            try:
                kind, payload = self.runner.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(str(payload))
            elif kind == "status":
                self._append_log(str(payload))
            elif kind == "exit":
                code = int(payload)
                self.status_var.set(f"运行结束，退出码 {code}")
                self._append_log(f"[结束] 退出码 {code}")
                self._refresh_dashboard()
        self.root.after(100, self._poll_runner_queue)

    def _refresh_dashboard(self) -> None:
        self._refresh_results()
        self._write_preflight_panel(self._build_current_preflight_report())
        cards = build_workbench_status_cards(
            Path(self.config_path_var.get()).expanduser(),
            self.config_data,
        )
        vpn_card, output_card, github_card = cards
        self.vpn_status_var.set(vpn_card.value)
        self.vpn_detail_var.set(vpn_card.detail)
        self.result_count_var.set(output_card.value)
        self.result_detail_var.set(f"443 占比 {output_card.detail}")
        self.github_status_var.set(github_card.value)
        self.github_detail_var.set(github_card.detail)
        for key, card in zip(("vpn", "result", "github"), cards):
            widget = self.status_accent_vars.get(key)
            if widget is not None:
                widget.configure(fg=card.accent)

    def _refresh_results(self) -> None:
        config_path = Path(self.config_path_var.get()).expanduser()
        output_file = resolve_output_path(config_path, self.config_data)
        self.output_file_var.set(str(output_file))

        try:
            lines = read_output_lines(config_path, self.config_data)
        except Exception as exc:
            lines = []
            self._append_log(f"[结果] 无法读取输出文件: {exc}")

        for listbox in (self.result_list, self.result_preview_list):
            if listbox is None:
                continue
            listbox.delete(0, self.tk.END)
            for line in lines:
                listbox.insert(self.tk.END, line)

        self.result_count_var.set(str(len(lines)))
        self.port_share_var.set(calculate_port_share(lines))
        if output_file.exists():
            updated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(output_file.stat().st_mtime))
            self.output_updated_var.set(updated)
        else:
            self.output_updated_var.set("未生成")
        self._refresh_backups()

    def _refresh_backups(self) -> None:
        config_path = Path(self.config_path_var.get()).expanduser()
        try:
            self.backup_paths = list_output_backups(config_path, self.config_data)
        except Exception as exc:
            self.backup_paths = []
            self._append_log(f"[备份] 无法读取备份列表: {exc}")
        self.backup_count_var.set(str(len(self.backup_paths)))
        if self.backup_list is None:
            return
        self.backup_list.delete(0, self.tk.END)
        for path in self.backup_paths:
            self.backup_list.insert(self.tk.END, format_backup_label(path))

    def _restore_selected_backup(self) -> None:
        if self.backup_list is None:
            return
        selection = self.backup_list.curselection()
        if not selection:
            self.messagebox.showinfo("未选择备份", "请先选择一份历史备份。")
            return
        backup_path = self.backup_paths[selection[0]]
        if not self.messagebox.askyesno("恢复备份", build_restore_confirmation_message(backup_path)):
            return
        try:
            restored_path = restore_output_backup(
                backup_path,
                Path(self.config_path_var.get()).expanduser(),
                self.config_data,
            )
        except Exception as exc:
            self.messagebox.showerror("恢复失败", f"无法恢复备份：{exc}")
            return
        self._append_log(f"[备份] 已恢复 {backup_path.name} -> {restored_path}")
        self.status_var.set(f"已恢复备份 {backup_path.name}")
        self._refresh_results()

    def _open_output_folder(self) -> None:
        folder = Path(self.output_file_var.get() or self.config_path_var.get()).expanduser().parent
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(folder)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            self.messagebox.showerror("打开失败", f"无法打开目录：{exc}")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DesktopApp().run()


if __name__ == "__main__":
    main()
