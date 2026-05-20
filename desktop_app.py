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

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageTk

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
class WorkbenchAction:
    key: str
    label: str
    hint: str
    icon: str
    accent: str


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

NAV_ITEM_GLYPHS = {
    "workbench": "Run",
    "results": "IP",
    "settings": "Set",
    "logs": "Log",
}

PAGE_TITLES = {
    "workbench": "工作台",
    "results": "结果",
    "settings": "应用设置",
    "logs": "日志/帮助",
}

APP_TOOLBAR_ACTIONS: List[ToolbarAction] = [
    ToolbarAction("refresh_dashboard", "刷新检查", "ghost"),
    ToolbarAction("save_config", "保存配置", "secondary"),
    ToolbarAction("open_output_folder", "输出目录", "soft"),
]

WORKBENCH_ACTIONS: List[WorkbenchAction] = [
    WorkbenchAction("optimize_only", "只运行优选", "断开 VPN 后本地直连测速", "RUN", "#2563eb"),
    WorkbenchAction("optimize_sync", "优选后自动上传", "完成后按设置同步到 GitHub", "AUTO", "#0f766e"),
    WorkbenchAction("sync_only", "上传到 GitHub", "只同步当前 ip.txt", "GH", "#16a34a"),
    WorkbenchAction("proxy_test", "测试 GitHub 代理", "只验证代理连通性", "TEST", "#0f766e"),
    WorkbenchAction("stop_task", "停止任务", "中断正在运行的流程", "STOP", "#dc2626"),
    WorkbenchAction("save_config", "保存设置", "写回 config.json", "SAVE", "#2563eb"),
    WorkbenchAction("refresh_dashboard", "刷新状态", "重新读取状态", "REF", "#475569"),
    WorkbenchAction("open_output_folder", "输出目录", "查看备份", "DIR", "#7c3aed"),
]

WORKBENCH_PRIMARY_ACTIONS = ["optimize_only", "optimize_sync", "sync_only", "proxy_test"]
WORKBENCH_SECONDARY_ACTIONS = ["stop_task", "save_config", "refresh_dashboard", "open_output_folder"]
WORKBENCH_ACTION_BY_KEY = {action.key: action for action in WORKBENCH_ACTIONS}

COCKPIT_LAYOUT = {
    "card_radius": 28,
    "panel_radius": 30,
    "chip_radius": 21,
    "main_task_height": 360,
    "action_tile_height": 108,
    "compact_tool_height": 42,
    "setting_row_height": 100,
    "setting_description_wrap": 600,
}

PAGE_TAB_STYLE = {
    "width": 132,
    "height": 42,
    "radius": 20,
    "active_fill": "#dbeafe",
    "active_border": "#bfdbfe",
    "active_text": "#1d4ed8",
    "inactive_fill": "#ffffff",
    "inactive_border": "#eef2f7",
    "inactive_text": "#475569",
    "hover_fill": "#f8fbff",
    "hover_border": "#bfdbfe",
    "hover_shadow_alpha": 36,
    "active_shadow_alpha": 22,
}

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

SETTING_DESCRIPTIONS = {
    "USE_GLOBAL_MODE": "使用全局 TopN 输出策略，适合统一控制总量。",
    "GLOBAL_TOP_N": "全局模式下最终保留的候选数量。",
    "PER_COUNTRY_TOP_N": "分国家模式下每个国家保留的节点数。",
    "BANDWIDTH_CANDIDATES": "进入带宽测速阶段的候选池大小。",
    "OUTPUT_NODE_LIMIT": "写入 ip.txt 的最终节点上限。",
    "MIN_SUCCESS_RATE": "TCP 可用性筛选的最低成功率。",
    "TIMEOUT": "单次 TCP 探测超时时间。",
    "TCP_PROBES": "每个节点 TCP 探测次数。",
    "BANDWIDTH_SIZE_MB": "下载测速使用的数据大小。",
    "TEST_AVAILABILITY": "优选前先做可用性检测。",
    "STABILITY_SCORING_ENABLED": "结合历史结果给节点稳定性加权。",
    "FILTER_COUNTRIES_ENABLED": "只输出允许国家列表中的节点。",
    "ENABLE_CF_OFFICIAL_IP_SAMPLING": "从 Cloudflare 官方 IP 段抽样补充候选。",
    "CF_OFFICIAL_SAMPLE_PER_24": "每个 /24 网段抽取的 IP 数量。",
    "CF_OFFICIAL_SAMPLE_PORTS": "官方采样时使用的端口列表。",
    "LOCAL_SEED_FILES": "本地全量 IP 或重要 IP 种子文件。",
    "ALLOWED_COUNTRIES": "允许输出的国家或地区代码。",
    "FILTER_BLOCKED_COUNTRIES_ENABLED": "启用屏蔽国家过滤。",
    "BLOCKED_COUNTRIES": "需要排除的国家或地区代码。",
    "OUTPUT_FILE": "最终订阅源输出文件。",
    "BACKUP_OUTPUT_ENABLED": "覆盖 ip.txt 前自动保存旧版本。",
    "OUTPUT_BACKUP_DIR": "历史备份保存目录。",
    "OUTPUT_BACKUP_KEEP": "最多保留的备份份数。",
    "STABILITY_STATS_FILE": "历史稳定性统计数据文件。",
    "LOG_FILE": "运行日志输出文件。",
    "CF_ENABLED": "是否启用 Cloudflare DNS 更新。",
    "DNS_UPDATE_TARGET_COUNT": "同步 DNS 时使用的节点数量。",
    "ENABLE_WXPUSHER": "运行结束后发送 WxPusher 通知。",
    "GITHUB_SYNC_ENABLED": "优选完成后是否自动同步 GitHub。",
    "GITHUB_SYNC_PROXY_URL": "GitHub 上传阶段使用的代理地址。",
    "GITHUB_SYNC_MAX_RETRIES": "GitHub 同步失败后的重试次数。",
    "ENABLE_LOGGING": "把运行过程写入日志文件。",
    "MAX_WORKERS": "主测速流程最大并发线程。",
    "AVAILABILITY_WORKERS": "可用性检测并发线程。",
    "BANDWIDTH_WORKERS": "带宽测速并发线程。",
    "AVAILABILITY_RETRY_MAX": "可用性检测失败重试次数。",
    "BANDWIDTH_RETRY_MAX": "带宽测速失败重试次数。",
    "CF_OFFICIAL_COUNTRY_CODE": "官方采样结果默认国家码。",
    "CF_DNS_RECORD_NAME": "Cloudflare DNS 记录名。",
}

COLORS = {
    "bg": "#f5f8fb",
    "sidebar": "#ffffff",
    "panel": "#ffffff",
    "soft_panel": "#f7f9fc",
    "card": "#ffffff",
    "border": "#d9e2ee",
    "text": "#0f172a",
    "muted": "#64748b",
    "muted_light": "#94a3b8",
    "blue": "#2563eb",
    "blue_dark": "#1d4ed8",
    "blue_soft": "#dbeafe",
    "teal": "#0f766e",
    "teal_soft": "#ccfbf1",
    "green": "#16a34a",
    "red": "#dc2626",
    "input": "#eef2f7",
}


def accent_surface(accent: str) -> str:
    return {
        COLORS["blue"]: "#dbeafe",
        COLORS["blue_dark"]: "#dbeafe",
        COLORS["teal"]: "#ccfbf1",
        COLORS["green"]: "#dcfce7",
        COLORS["red"]: "#fee2e2",
        COLORS["muted"]: "#e2e8f0",
        "#7c3aed": "#ede9fe",
    }.get(accent, COLORS["blue_soft"])


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    return ImageColor.getrgb(hex_color)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _blend_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def _blend_hex(a: str, b: str, t: float) -> str:
    return _rgb_to_hex(_blend_rgb(_hex_to_rgb(a), _hex_to_rgb(b), t))


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)


def _load_badge_font(size: int) -> ImageFont.ImageFont:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windir / "Fonts" / "segoeuib.ttf",
        windir / "Fonts" / "segoeui.ttf",
        windir / "Fonts" / "arialbd.ttf",
        windir / "Fonts" / "arial.ttf",
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_badge_image(
    label: str,
    accent: str,
    size: int = 40,
    background: str | None = None,
    border: str | None = None,
    text_color: str | None = None,
) -> Image.Image:
    bg = background or accent_surface(accent)
    outline = border or "#d7e2f0"
    foreground = text_color or accent
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [1, 1, size - 2, size - 2],
        radius=max(8, size // 4),
        fill=_hex_to_rgb(bg),
        outline=_hex_to_rgb(outline),
        width=1,
    )
    font_size = max(12, int(size * 0.34))
    font = _load_badge_font(font_size)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1] - 1
    draw.text((x, y), label, font=font, fill=_hex_to_rgb(foreground))
    return image


def render_logo_image(size: int = 44) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    start = _hex_to_rgb(COLORS["blue"])
    end = _hex_to_rgb("#0ea5a5")
    radius = max(14, size // 3)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_pixels = gradient.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / max(1, (size - 1) * 2)
            color = tuple(int(start[i] * (1 - t) + end[i] * t) for i in range(3))
            gradient_pixels[x, y] = (*color, 255)
    image = Image.composite(gradient, image, mask)
    highlight = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.rounded_rectangle(
        [4, 4, size - 5, int(size * 0.55)],
        radius=radius,
        fill=(255, 255, 255, 26),
    )
    image = Image.alpha_composite(image, highlight)
    font = _load_badge_font(max(13, int(size * 0.38)))
    bbox = draw.textbbox((0, 0), "cf", font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw = ImageDraw.Draw(image)
    draw.text(
        ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1] - 1),
        "cf",
        font=font,
        fill=(255, 255, 255, 255),
    )
    return image


def render_rounded_surface(
    width: int,
    height: int,
    fill: str,
    border: str,
    radius: int = 20,
    shadow: bool = True,
    shadow_alpha: int = 34,
    shadow_offset: tuple[int, int] = (4, 6),
    shadow_blur: int = 9,
) -> Image.Image:
    width = max(2, int(width))
    height = max(2, int(height))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    if shadow:
        shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        offset_x, offset_y = shadow_offset
        shadow_draw.rounded_rectangle(
            [offset_x, offset_y, width - max(2, offset_x + 2), height - max(2, offset_y + 1)],
            radius=max(1, radius),
            fill=(15, 23, 42, max(0, min(255, shadow_alpha))),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(max(1, shadow_blur)))
        image = Image.alpha_composite(image, shadow_layer)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [1, 1, width - 2, height - 2],
        radius=max(1, radius),
        fill=_hex_to_rgb(fill),
        outline=_hex_to_rgb(border),
        width=1,
    )
    return image


def render_page_tab_image(width: int, height: int, active: bool = False, hover: bool = False) -> Image.Image:
    width = max(2, int(width))
    height = max(2, int(height))
    radius = min(PAGE_TAB_STYLE["radius"], max(1, height // 2))
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_alpha = 0
    if hover:
        shadow_alpha = PAGE_TAB_STYLE["hover_shadow_alpha"]
    elif active:
        shadow_alpha = PAGE_TAB_STYLE["active_shadow_alpha"]

    if shadow_alpha:
        shadow_mask = Image.new("L", (width, height), 0)
        mask_draw = ImageDraw.Draw(shadow_mask)
        mask_draw.rounded_rectangle(
            [6, 7, width - 7, height - 5],
            radius=radius,
            fill=shadow_alpha,
        )
        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(7))
        shadow = Image.new("RGBA", (width, height), (*_hex_to_rgb(COLORS["blue_dark"]), 0))
        shadow.putalpha(shadow_mask)
        image = Image.alpha_composite(image, shadow)

    if active:
        fill = PAGE_TAB_STYLE["active_fill"]
        border = PAGE_TAB_STYLE["active_border"]
    elif hover:
        fill = PAGE_TAB_STYLE["hover_fill"]
        border = PAGE_TAB_STYLE["hover_border"]
    else:
        fill = PAGE_TAB_STYLE["inactive_fill"]
        border = PAGE_TAB_STYLE["inactive_border"]

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [3, 3, width - 4, height - 4],
        radius=radius,
        fill=_hex_to_rgb(fill),
        outline=_hex_to_rgb(border),
        width=1,
    )
    return image


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
        self.vpn_detail_var = tk.StringVar(value="测速走本地直连")
        self.result_detail_var = tk.StringVar(value="443 优先输出")
        self.github_detail_var = tk.StringVar(value="上传走代理")
        self.backup_count_var = tk.StringVar(value="0")
        self.backup_detail_var = tk.StringVar(value="保留 20 份")
        self.output_file_var = tk.StringVar(value="")
        self.banner_text_var = tk.StringVar(value="直连测速，代理上传")
        self.status_accent_vars: Dict[str, Any] = {}

        self.config_data: Dict[str, Any] = {}
        self.form_vars: Dict[str, Any] = {}
        self.page_frames: Dict[str, Any] = {}
        self.nav_buttons: Dict[str, Any] = {}
        self.nav_labels: Dict[str, Any] = {}
        self.page_tab_buttons: Dict[str, Any] = {}
        self.toolbar_buttons: Dict[str, Any] = {}
        self.badge_images: Dict[str, Any] = {}
        self.surface_images: Dict[str, Any] = {}
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

        sidebar_host = tk.Frame(shell, bg=COLORS["bg"], width=102)
        sidebar_host.grid(row=0, column=0, sticky="ns")
        sidebar_host.grid_propagate(False)

        sidebar = tk.Frame(sidebar_host, bg=COLORS["bg"], width=68, height=610, highlightthickness=0)
        sidebar.pack(expand=True, padx=(24, 10))
        sidebar.pack_propagate(False)
        self._install_rounded_surface(
            sidebar,
            fill=COLORS["sidebar"],
            border="#e2e8f0",
            radius=30,
            shadow=True,
            cache_key="sidebar-shell",
        )

        logo = ImageTk.PhotoImage(render_logo_image(44), master=self.root)
        self.badge_images["app-logo"] = logo
        logo_label = tk.Label(sidebar, image=logo, bg=COLORS["sidebar"], bd=0)
        logo_label.image = logo
        logo_label.pack(pady=(30, 28))
        for item in NAV_ITEMS:
            nav_shell = tk.Frame(sidebar, bg=COLORS["sidebar"], width=44, height=44)
            nav_shell.pack(padx=12, pady=10)
            nav_shell.pack_propagate(False)
            self._install_rounded_surface(
                nav_shell,
                fill=COLORS["sidebar"],
                border=COLORS["sidebar"],
                radius=18,
                shadow=False,
                cache_key=f"nav-shell-{item.key}",
            )
            badge = self._badge_photo(
                f"nav-{item.key}-inactive",
                NAV_ITEM_GLYPHS[item.key],
                COLORS["muted"],
                size=28,
                background=COLORS["sidebar"],
                border=COLORS["sidebar"],
            )
            icon = tk.Label(nav_shell, image=badge, bg=COLORS["sidebar"], bd=0)
            icon.image = badge
            icon.pack(expand=True)
            nav_shell._nav_icon = icon
            nav_shell._nav_item = item
            self._bind_click_recursive(nav_shell, lambda key=item.key: self._show_page(key))
            self.nav_buttons[item.key] = nav_shell
            self.nav_labels[item.key] = None

        tk.Label(sidebar, text="手动", bg=COLORS["sidebar"], fg=COLORS["muted_light"], font=("Microsoft YaHei UI", 9)).pack(side="bottom", pady=(0, 24))

        main = tk.Frame(shell, bg=COLORS["bg"])
        main.grid(row=0, column=1, sticky="nsew", padx=(8, 30), pady=22)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = tk.Frame(main, bg=COLORS["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=0)
        title_stack = tk.Frame(header, bg=COLORS["bg"])
        title_stack.grid(row=0, column=0, sticky="w")
        tk.Label(title_stack, textvariable=self.page_title_var, bg=COLORS["bg"], fg=COLORS["blue_dark"], font=("Microsoft YaHei UI", 19, "bold")).pack(anchor="w")
        tk.Label(title_stack, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(5, 0))

        banner = tk.Frame(header, bg=COLORS["bg"], width=430, height=58, highlightthickness=0)
        banner.grid(row=0, column=1, padx=(22, 16))
        banner.grid_propagate(False)
        self._install_rounded_surface(
            banner,
            fill=COLORS["panel"],
            border="#d8e1ec",
            radius=29,
            shadow=True,
            cache_key="top-banner",
        )
        banner_inner = tk.Frame(banner, bg=COLORS["panel"])
        banner_inner.pack(fill="both", expand=True, padx=14, pady=9)
        tk.Label(banner_inner, text="提示", bg=COLORS["blue_soft"], fg=COLORS["blue_dark"], font=("Microsoft YaHei UI", 8, "bold"), padx=10, pady=5).pack(side="left")
        tk.Label(banner_inner, textvariable=self.banner_text_var, bg=COLORS["panel"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(side="left", padx=(12, 8))
        tk.Frame(banner_inner, bg=COLORS["panel"]).pack(side="left", fill="x", expand=True)
        self._primary_button(banner_inner, "代理", self._start_proxy_test, variant="soft").pack(side="right")

        toolbar = tk.Frame(header, bg=COLORS["bg"])
        toolbar.grid(row=0, column=2, sticky="e")
        for action in APP_TOOLBAR_ACTIONS:
            button = self._primary_button(
                toolbar,
                action.label,
                lambda key=action.key: self._run_toolbar_action(key),
                variant=action.variant,
            )
            button.pack(side="left", padx=(8, 0))
            self.toolbar_buttons[action.key] = button

        page_switcher = tk.Frame(main, bg=COLORS["bg"], width=628, height=58)
        page_switcher.grid(row=1, column=0, pady=(0, 16))
        page_switcher.grid_propagate(False)
        self._install_rounded_surface(
            page_switcher,
            fill=COLORS["panel"],
            border="#e2e8f0",
            radius=29,
            shadow=True,
            cache_key="page-switcher",
        )
        for index in range(len(NAV_ITEMS)):
            page_switcher.grid_columnconfigure(index, weight=1, uniform="page-tabs")
        for index, item in enumerate(NAV_ITEMS):
            tab = self._page_tab_button(
                page_switcher,
                item,
                lambda key=item.key: self._show_page(key),
                active=item.key == self.active_page,
            )
            tab.grid(row=0, column=index, padx=(10 if index == 0 else 5, 10 if index == len(NAV_ITEMS) - 1 else 5), pady=8, sticky="nsew")
            self.page_tab_buttons[item.key] = tab

        self.content_host = tk.Frame(main, bg=COLORS["bg"])
        self.content_host.grid(row=2, column=0, sticky="nsew")
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
            bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=0,
            bd=0,
        )
        self._install_rounded_surface(
            frame,
            fill=COLORS["card"],
            border="#d8e1ec",
            radius=COCKPIT_LAYOUT["card_radius"],
            shadow=True,
            cache_key=f"card-{id(frame)}",
        )
        if title:
            self.tk.Label(frame, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", padx=padding, pady=(padding, 4))
        if subtitle:
            self.tk.Label(frame, text=subtitle, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), justify="left", anchor="w", wraplength=720).pack(anchor="w", padx=padding, pady=(0, 4))
        return frame

    def _install_rounded_surface(
        self,
        widget: Any,
        fill: str,
        border: str,
        radius: int = 18,
        shadow: bool = True,
        cache_key: str | None = None,
    ) -> None:
        background = widget.cget("bg") if hasattr(widget, "cget") else COLORS["bg"]
        bg_label = self.tk.Label(widget, bg=background, bd=0, highlightthickness=0)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        bg_label.lower()
        widget._surface_bg_label = bg_label
        widget._surface_fill = fill
        widget._surface_border = border
        widget._surface_radius = radius
        widget._surface_shadow = shadow
        widget._surface_shadow_alpha = 34 if shadow else 0
        widget._surface_shadow_offset = (4, 6)
        widget._surface_shadow_blur = 9
        widget._surface_cache_key = cache_key or f"surface-{id(widget)}"

        def redraw(_event: Any | None = None) -> None:
            width = max(2, widget.winfo_width())
            height = max(2, widget.winfo_height())
            if width < 4 or height < 4:
                return
            image = render_rounded_surface(
                width,
                height,
                widget._surface_fill,
                widget._surface_border,
                radius=widget._surface_radius,
                shadow=widget._surface_shadow,
                shadow_alpha=getattr(widget, "_surface_shadow_alpha", 34),
                shadow_offset=getattr(widget, "_surface_shadow_offset", (4, 6)),
                shadow_blur=getattr(widget, "_surface_shadow_blur", 9),
            )
            cache_key_local = (
                f"{widget._surface_cache_key}:{width}x{height}:"
                f"{widget._surface_fill}:{widget._surface_border}:"
                f"{widget._surface_radius}:{widget._surface_shadow}"
            )
            photo = ImageTk.PhotoImage(image, master=self.root)
            self.surface_images[cache_key_local] = photo
            bg_label.configure(image=photo)
            bg_label.image = photo

        widget._surface_redraw = redraw
        widget.bind("<Configure>", redraw, add="+")
        redraw()

    def _badge_photo(
        self,
        cache_key: str,
        label: str,
        accent: str,
        size: int = 40,
        background: str | None = None,
        border: str | None = None,
        text_color: str | None = None,
    ) -> Any:
        if cache_key not in self.badge_images:
            image = render_badge_image(label, accent, size=size, background=background, border=border, text_color=text_color)
            self.badge_images[cache_key] = ImageTk.PhotoImage(image, master=self.root)
        return self.badge_images[cache_key]

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
        accent_line = self.tk.Frame(frame, bg=accent, height=3)
        accent_line.pack(fill="x", padx=18, pady=(13, 0))
        body = self.tk.Frame(frame, bg=COLORS["card"])
        body.pack(fill="x", padx=14, pady=(11, 14))
        body.grid_columnconfigure(1, weight=1)

        badge = self._badge_photo(
            f"metric-{title}-{icon}",
            icon or title[:2],
            accent,
            size=44,
            background=accent_surface(accent),
        )
        icon_label = self.tk.Label(body, image=badge, bg=COLORS["card"])
        icon_label.image = badge
        icon_label.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))

        text_stack = self.tk.Frame(body, bg=COLORS["card"])
        text_stack.grid(row=0, column=1, sticky="ew")
        self.tk.Label(text_stack, text=title, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        value_label = self.tk.Label(text_stack, textvariable=variable, bg=COLORS["card"], fg=accent, font=("Microsoft YaHei UI", 19, "bold"))
        value_label.pack(anchor="w", pady=(2, 0))
        if detail_variable is not None:
            self.tk.Label(text_stack, textvariable=detail_variable, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), justify="left", anchor="w", wraplength=150).pack(anchor="w", pady=(0, 0))
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
        width = max(58, len(text) * 14 + 30)
        height = 36
        canvas_width = width + 4
        canvas_height = height + 4
        parent_bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg"]
        button = self.tk.Canvas(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg=parent_bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        button._button_variant = chosen_variant
        button._hover_progress = 0.0
        button._hover_anim_job = None
        button._button_text = text

        def draw_button(progress: float = 0.0, pressed: bool = False) -> None:
            progress = max(0.0, min(1.0, progress))
            next_variant = getattr(button, "_button_variant", chosen_variant)
            style = BUTTON_VARIANTS[next_variant]
            fill = _blend_hex(style["bg"], style["activebackground"], progress)
            fg = _blend_hex(style["fg"], style["activeforeground"], progress)
            border = _blend_hex(style["border"], style["activebackground"], progress * 0.45)
            shadow_alpha = int(round(24 + (18 if next_variant in {"primary", "secondary"} else 10) * progress))
            shadow_blur = 8 + int(round(progress))
            shadow_offset = (4, 6 - int(round(progress * 2)) + (1 if pressed else 0))
            image = render_rounded_surface(
                width,
                height,
                fill,
                border,
                radius=height // 2,
                shadow=True,
                shadow_alpha=shadow_alpha,
                shadow_offset=shadow_offset,
                shadow_blur=shadow_blur,
            )
            photo_key = f"button-{id(button)}:{next_variant}:{progress:.2f}"
            photo = ImageTk.PhotoImage(image, master=self.root)
            self.surface_images[photo_key] = photo
            button.delete("all")
            lift = int(round(progress * 2)) - (1 if pressed else 0)
            button.create_image(2, 2 - lift, image=photo, anchor="nw")
            button.create_text(
                canvas_width // 2,
                canvas_height // 2 - lift,
                text=button._button_text,
                fill=fg,
                font=("Microsoft YaHei UI", 10, "bold"),
            )
            button.image = photo

        def set_variant(next_variant: str) -> None:
            button._button_variant = next_variant
            button._hover_progress = 0.0
            draw_button(0.0)

        def animate_to(target: float) -> None:
            target = max(0.0, min(1.0, target))
            if button._hover_anim_job is not None:
                try:
                    button.after_cancel(button._hover_anim_job)
                except Exception:
                    pass
                button._hover_anim_job = None
            start = float(getattr(button, "_hover_progress", 0.0))
            if abs(target - start) < 0.01:
                button._hover_progress = target
                draw_button(target)
                return

            start_time = time.monotonic()
            duration_ms = 120

            def step() -> None:
                elapsed = (time.monotonic() - start_time) * 1000
                t = min(1.0, elapsed / duration_ms)
                eased = _ease_out_cubic(t)
                current = start + (target - start) * eased
                button._hover_progress = current
                draw_button(current)
                if t < 1.0:
                    button._hover_anim_job = button.after(16, step)
                else:
                    button._hover_anim_job = None

            step()

        button._set_button_variant = set_variant
        set_variant(chosen_variant)
        button.bind("<ButtonPress-1>", lambda _event: draw_button(float(getattr(button, "_hover_progress", 0.0)), pressed=True), add="+")
        button.bind("<ButtonRelease-1>", lambda _event: draw_button(float(getattr(button, "_hover_progress", 0.0)), pressed=False), add="+")
        button.bind("<Button-1>", lambda _event, cb=command: cb())
        button.bind("<Enter>", lambda _event: animate_to(1.0), add="+")
        button.bind("<Leave>", lambda _event: animate_to(0.0), add="+")
        return button

    def _page_tab_button(self, parent: Any, item: NavItem, command: Callable[[], None], active: bool = False) -> Any:
        width = PAGE_TAB_STYLE["width"]
        height = PAGE_TAB_STYLE["height"]
        parent_bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["panel"]
        tab = self.tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=parent_bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        tab._tab_active = bool(active)
        tab._tab_hover = False
        tab._tab_anim_job = None

        def draw_tab() -> None:
            is_active = bool(getattr(tab, "_tab_active", False))
            is_hover = bool(getattr(tab, "_tab_hover", False))
            image = render_page_tab_image(width, height, active=is_active, hover=is_hover)
            photo_key = f"page-tab-{item.key}:{is_active}:{is_hover}"
            photo = ImageTk.PhotoImage(image, master=self.root)
            self.surface_images[photo_key] = photo
            tab.delete("all")
            tab.create_image(0, 0, image=photo, anchor="nw")
            text_color = PAGE_TAB_STYLE["active_text"] if is_active else PAGE_TAB_STYLE["inactive_text"]
            if is_hover and not is_active:
                text_color = COLORS["blue_dark"]
            icon_color = text_color if is_active or is_hover else COLORS["muted"]
            tab.create_text(
                30,
                height // 2,
                text=NAV_ITEM_GLYPHS[item.key],
                fill=icon_color,
                font=("Microsoft YaHei UI", 8, "bold"),
                anchor="center",
            )
            tab.create_text(
                62,
                height // 2,
                text=item.label,
                fill=text_color,
                font=("Microsoft YaHei UI", 10, "bold"),
                anchor="w",
            )
            tab.image = photo

        def set_active(next_active: bool) -> None:
            tab._tab_active = bool(next_active)
            draw_tab()

        def set_hover(next_hover: bool) -> None:
            tab._tab_hover = bool(next_hover)
            draw_tab()

        tab._set_tab_active = set_active
        tab.bind("<Button-1>", lambda _event, cb=command: cb())
        tab.bind("<Enter>", lambda _event: set_hover(True), add="+")
        tab.bind("<Leave>", lambda _event: set_hover(False), add="+")
        draw_tab()
        return tab

    def _pill_label(self, parent: Any, text: str, fill: str, fg: str, border: str | None = None) -> Any:
        height = 34
        width = max(76, len(text) * 14 + 28)
        parent_bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["card"]
        pill = self.tk.Canvas(parent, width=width + 2, height=height + 2, bg=parent_bg, bd=0, highlightthickness=0)
        image = render_rounded_surface(
            width,
            height,
            fill,
            border or fill,
            radius=height // 2,
            shadow=False,
        )
        photo_key = f"pill-{id(pill)}-{text}"
        photo = ImageTk.PhotoImage(image, master=self.root)
        self.surface_images[photo_key] = photo
        pill.create_image(1, 1, image=photo, anchor="nw")
        pill.create_text((width + 2) // 2, (height + 2) // 2, text=text, fill=fg, font=("Microsoft YaHei UI", 9, "bold"))
        pill.image = photo
        return pill

    def _entry_control(self, parent: Any, variable: Any, width: int = 256) -> Any:
        control = self.tk.Frame(parent, bg=COLORS["card"], width=width, height=38, bd=0, highlightthickness=0)
        control.grid_propagate(False)
        control.pack_propagate(False)
        self._install_rounded_surface(
            control,
            fill="#eef3f8",
            border="#ccd6e3",
            radius=14,
            shadow=False,
            cache_key=f"entry-control-{id(control)}",
        )
        entry = self.tk.Entry(
            control,
            textvariable=variable,
            relief="flat",
            bg="#eef3f8",
            fg=COLORS["text"],
            insertbackground=COLORS["blue_dark"],
            bd=0,
            highlightthickness=0,
            font=("Microsoft YaHei UI", 10),
        )
        entry.pack(fill="both", expand=True, padx=14, pady=7)

        def set_focus(active: bool) -> None:
            control._surface_border = "#93c5fd" if active else "#ccd6e3"
            control._surface_fill = "#f8fbff" if active else "#eef3f8"
            entry.configure(bg=control._surface_fill)
            if hasattr(control, "_surface_redraw"):
                control._surface_redraw()

        entry.bind("<FocusIn>", lambda _event: set_focus(True), add="+")
        entry.bind("<FocusOut>", lambda _event: set_focus(False), add="+")
        return control

    def _toggle_control(self, parent: Any, variable: Any, width: int = 92) -> Any:
        height = 34
        toggle = self.tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["card"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        toggle._toggle_hover = False

        def draw_toggle() -> None:
            enabled = bool(variable.get())
            hover = bool(getattr(toggle, "_toggle_hover", False))
            fill = "#dbeafe" if enabled else "#eef3f8"
            border = "#93c5fd" if enabled else "#ccd6e3"
            if hover:
                fill = _blend_hex(fill, "#ffffff", 0.18)
                border = _blend_hex(border, COLORS["blue"], 0.24)
            fg = COLORS["blue_dark"] if enabled else COLORS["muted"]
            label = "开启" if enabled else "关闭"
            image = render_rounded_surface(
                width,
                height,
                fill,
                border,
                radius=height // 2,
                shadow=hover,
                shadow_alpha=28,
                shadow_offset=(3, 4),
                shadow_blur=7,
            )
            photo_key = f"toggle-{id(toggle)}:{enabled}:{hover}"
            photo = ImageTk.PhotoImage(image, master=self.root)
            self.surface_images[photo_key] = photo
            toggle.delete("all")
            toggle.create_image(0, 0, image=photo, anchor="nw")
            toggle.create_text(width // 2, height // 2, text=label, fill=fg, font=("Microsoft YaHei UI", 10, "bold"))
            toggle.image = photo

        def flip() -> None:
            variable.set(not bool(variable.get()))

        variable.trace_add("write", lambda *_args: draw_toggle())
        toggle.bind("<Button-1>", lambda _event: flip(), add="+")
        toggle.bind("<Enter>", lambda _event: (setattr(toggle, "_toggle_hover", True), draw_toggle()), add="+")
        toggle.bind("<Leave>", lambda _event: (setattr(toggle, "_toggle_hover", False), draw_toggle()), add="+")
        draw_toggle()
        return toggle

    def _bind_click_recursive(self, widget: Any, command: Callable[[], None]) -> None:
        widget.configure(cursor="hand2")
        widget.bind("<Button-1>", lambda _event, cb=command: cb())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, command)

    def _build_action_tile(self, parent: Any, action: WorkbenchAction, command: Callable[[], None]) -> Any:
        base_border = "#93c5fd" if action.key == "optimize_only" else "#e1e8f2"
        hover_border = "#2563eb" if action.key == "optimize_only" else "#bfd5f2"
        tile = self.tk.Frame(
            parent,
            bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["card"],
            highlightbackground="#d8e2ee",
            highlightthickness=0,
            bd=0,
            height=COCKPIT_LAYOUT["action_tile_height"],
        )
        tile.grid_propagate(False)
        self._install_rounded_surface(
            tile,
            fill="#ffffff",
            border=base_border,
            radius=24,
            shadow=True,
            cache_key=f"action-{action.key}",
        )
        tile.grid_columnconfigure(1, weight=1)
        tile.grid_rowconfigure(0, weight=1)
        tile._hover_progress = 0.0
        tile._hover_anim_job = None
        tile._surface_shadow_alpha = 34 if action.key == "optimize_only" else 30
        tile._surface_shadow_offset = (4, 6)
        tile._surface_shadow_blur = 9

        badge = self._badge_photo(
            f"action-{action.key}",
            action.icon,
            action.accent,
            size=46,
            background=accent_surface(action.accent),
        )
        icon = self.tk.Label(tile, image=badge, bg="#ffffff")
        icon.image = badge
        icon.grid(row=0, column=0, rowspan=2, sticky="nw", padx=14, pady=16)

        text_stack = self.tk.Frame(tile, bg="#ffffff")
        text_stack.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=(16, 0))
        title_label = self.tk.Label(text_stack, text=action.label, bg="#ffffff", fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold"), justify="left", anchor="w", wraplength=230)
        title_label.pack(anchor="w")
        hint_label = self.tk.Label(text_stack, text=action.hint, bg="#ffffff", fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), justify="left", anchor="w", wraplength=240)
        hint_label.pack(anchor="w", pady=(5, 0))

        hover_children = [icon, text_stack, title_label, hint_label]

        def draw_tile(progress: float) -> None:
            progress = max(0.0, min(1.0, progress))
            fill = _blend_hex("#ffffff", "#f7fbff", progress)
            border = _blend_hex(base_border, hover_border, progress)
            shadow_alpha = int(round((32 if action.key == "optimize_only" else 28) + 8 * progress))
            shadow_blur = 8 + int(round(progress))
            shadow_offset = (4, 6 - int(round(progress)))
            tile._surface_fill = fill
            tile._surface_border = border
            tile._surface_shadow = True
            tile._surface_shadow_alpha = shadow_alpha
            tile._surface_shadow_offset = shadow_offset
            tile._surface_shadow_blur = shadow_blur
            if hasattr(tile, "_surface_redraw"):
                tile._surface_redraw()
            for child in hover_children:
                child.configure(bg=fill)

        def animate_tile(target: float) -> None:
            target = max(0.0, min(1.0, target))
            if tile._hover_anim_job is not None:
                try:
                    tile.after_cancel(tile._hover_anim_job)
                except Exception:
                    pass
                tile._hover_anim_job = None
            start = float(getattr(tile, "_hover_progress", 0.0))
            if abs(target - start) < 0.01:
                tile._hover_progress = target
                draw_tile(target)
                return

            start_time = time.monotonic()
            duration_ms = 110

            def step() -> None:
                elapsed = (time.monotonic() - start_time) * 1000
                t = min(1.0, elapsed / duration_ms)
                eased = _ease_out_cubic(t)
                current = start + (target - start) * eased
                tile._hover_progress = current
                draw_tile(current)
                if t < 1.0:
                    tile._hover_anim_job = tile.after(16, step)
                else:
                    tile._hover_anim_job = None

            step()

        self._bind_click_recursive(tile, command)
        tile.bind("<Enter>", lambda _event: animate_tile(1.0), add="+")
        tile.bind("<Leave>", lambda _event: animate_tile(0.0), add="+")
        return tile

    def _status_chip(
        self,
        parent: Any,
        title: str,
        variable: Any,
        detail_variable: Any | None,
        accent: str,
        icon: str,
    ) -> Any:
        chip = self.tk.Frame(parent, bg=parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg"], height=76)
        chip.grid_propagate(False)
        chip.grid_columnconfigure(1, weight=1)
        self._install_rounded_surface(
            chip,
            fill="#ffffff",
            border="#dfe8f3",
            radius=24,
            shadow=True,
            cache_key=f"status-chip-{title}-{id(chip)}",
        )
        badge = self._badge_photo(
            f"status-chip-{title}-{icon}",
            icon,
            accent,
            size=38,
            background=accent_surface(accent),
        )
        icon_label = self.tk.Label(chip, image=badge, bg="#ffffff", bd=0)
        icon_label.image = badge
        icon_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(14, 10), pady=18)
        self.tk.Label(chip, text=title, bg="#ffffff", fg=COLORS["muted"], font=("Microsoft YaHei UI", 8, "bold")).grid(row=0, column=1, sticky="sw", padx=(0, 12), pady=(14, 0))
        value_label = self.tk.Label(chip, textvariable=variable, bg="#ffffff", fg=accent, font=("Microsoft YaHei UI", 11, "bold"), anchor="w")
        value_label.grid(row=1, column=1, sticky="nw", padx=(0, 12), pady=(2, 0))
        if detail_variable is not None:
            detail_label = self.tk.Label(chip, textvariable=detail_variable, bg="#ffffff", fg=COLORS["muted"], font=("Microsoft YaHei UI", 8), anchor="e", justify="right", wraplength=150)
            detail_label.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 14))
        chip.value_label = value_label
        return chip

    def _build_compact_tool_button(self, parent: Any, action: WorkbenchAction, command: Callable[[], None]) -> Any:
        variant = "danger" if action.key == "stop_task" else "secondary"
        label = f"{action.icon}  {action.label}" if action.key != "open_output_folder" else action.label
        return self._primary_button(parent, label, command, variant=variant)

    def _build_main_task_card(self, parent: Any) -> Any:
        card = self._card(parent)
        card.configure(height=COCKPIT_LAYOUT["main_task_height"])
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(1, weight=1)

        badge = self._badge_photo("main-task-badge", "cf", COLORS["blue"], size=62, background=COLORS["blue_soft"], border="#bfdbfe")
        badge_label = self.tk.Label(card, image=badge, bg=COLORS["card"], bd=0)
        badge_label.image = badge
        badge_label.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(22, 16), pady=(24, 0))

        header = self.tk.Frame(card, bg=COLORS["card"])
        header.grid(row=0, column=1, sticky="ew", padx=(0, 22), pady=(22, 0))
        header.grid_columnconfigure(0, weight=1)
        title_stack = self.tk.Frame(header, bg=COLORS["card"])
        title_stack.grid(row=0, column=0, sticky="w")
        self.tk.Label(title_stack, text="Cloudflare IP 优选任务", bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        self.tk.Label(title_stack, textvariable=self.banner_text_var, bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(5, 0))
        chip = self._pill_label(header, "手动流程", "#dcfce7", "#166534", "#bbf7d0")
        chip.grid(row=0, column=1, sticky="e")

        actions = self.tk.Frame(card, bg=COLORS["card"])
        actions.grid(row=1, column=1, sticky="nsew", padx=(0, 22), pady=(18, 22))
        for col in range(2):
            actions.grid_columnconfigure(col, weight=1, uniform="main-actions")
        for index, action_key in enumerate(WORKBENCH_PRIMARY_ACTIONS):
            action = WORKBENCH_ACTION_BY_KEY[action_key]
            tile = self._build_action_tile(actions, action, lambda key=action.key: self._run_workbench_action(key))
            tile.grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0 if index % 2 == 0 else 10, 10 if index % 2 == 0 else 0), pady=(0 if index < 2 else 10, 0))
        return card

    def _build_workbench_page(self) -> None:
        page = self.tk.Frame(self.content_host, bg=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=5)
        page.grid_columnconfigure(1, weight=3)
        page.grid_rowconfigure(2, weight=1)
        self.page_frames["workbench"] = page

        status_strip = self.tk.Frame(page, bg=COLORS["bg"])
        status_strip.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        for col in range(4):
            status_strip.grid_columnconfigure(col, weight=1, uniform="status-strip")
        vpn_chip = self._status_chip(status_strip, "VPN/代理", self.vpn_status_var, self.vpn_detail_var, COLORS["red"], "VPN")
        vpn_chip.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.status_accent_vars["vpn"] = vpn_chip.value_label
        result_chip = self._status_chip(status_strip, "当前 ip.txt", self.result_count_var, self.output_updated_var, COLORS["blue_dark"], "IP")
        result_chip.grid(row=0, column=1, sticky="ew", padx=8)
        self.status_accent_vars["result"] = result_chip.value_label
        share_chip = self._status_chip(status_strip, "443 占比", self.port_share_var, self.result_detail_var, COLORS["teal"], "443")
        share_chip.grid(row=0, column=2, sticky="ew", padx=8)
        github_chip = self._status_chip(status_strip, "GitHub", self.github_status_var, self.github_detail_var, COLORS["green"], "GH")
        github_chip.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        self.status_accent_vars["github"] = github_chip.value_label

        left = self.tk.Frame(page, bg=COLORS["bg"])
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 14))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        task_card = self._build_main_task_card(left)
        task_card.grid(row=0, column=0, sticky="ew", pady=(0, 14))

        tool_bar = self._card(left, "工具")
        tool_bar.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        tools = self.tk.Frame(tool_bar, bg=COLORS["card"])
        tools.pack(fill="x", padx=18, pady=(8, 18))
        for action_key in WORKBENCH_SECONDARY_ACTIONS:
            action = WORKBENCH_ACTION_BY_KEY[action_key]
            button = self._build_compact_tool_button(tools, action, lambda key=action.key: self._run_workbench_action(key))
            button.pack(side="left", padx=(0, 10))

        preview_card = self._card(left, "最新结果预览", "443 优先输出，客户端继续二次优选。")
        preview_card.grid(row=2, column=0, sticky="nsew")
        preview_meta = self.tk.Frame(preview_card, bg=COLORS["card"])
        preview_meta.pack(fill="x", padx=18, pady=(4, 10))
        self.tk.Label(preview_meta, text="443 占比", bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")
        self.tk.Label(preview_meta, textvariable=self.port_share_var, bg=COLORS["card"], fg=COLORS["blue_dark"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=(8, 20))
        self.tk.Label(preview_meta, text="更新时间", bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")
        self.tk.Label(preview_meta, textvariable=self.output_updated_var, bg=COLORS["card"], fg=COLORS["text"]).pack(side="left", padx=(8, 0))
        self.result_preview_list = self.tk.Listbox(preview_card, height=8, relief="flat", bd=0, bg="#f8fbff", fg=COLORS["text"], font=("Consolas", 10))
        self.result_preview_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        right = self.tk.Frame(page, bg=COLORS["bg"])
        right.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        preflight_card = self._card(right, "运行前检查")
        preflight_card.grid(row=0, column=0, sticky="nsew", pady=(0, 14))
        self.preflight_text = self.scrolledtext.ScrolledText(preflight_card, wrap="word", height=16, state="disabled", relief="flat", bg="#f8fbff")
        self.preflight_text.pack(fill="both", expand=True, padx=18, pady=(8, 18))

        log_card = self._card(right, "运行日志")
        log_card.grid(row=1, column=0, sticky="nsew")
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        self.dashboard_log_text = self.scrolledtext.ScrolledText(log_card, wrap="word", height=8, state="disabled", relief="flat", bg="#f8fbff")
        self.dashboard_log_text.pack(fill="both", expand=True, padx=18, pady=(8, 18))

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

        top = self._card(page, "配置文件", "本地配置保留在 config.json，高级页可直接编辑完整 JSON。")
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
        tabs_host = self.tk.Frame(body, bg=COLORS["card"])
        tabs_host.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        tabs_host.grid_columnconfigure(0, weight=1)
        tabs_host.grid_columnconfigure(2, weight=1)
        tabs = self.tk.Frame(tabs_host, bg=COLORS["card"])
        tabs.grid(row=0, column=1)
        self._install_rounded_surface(
            tabs,
            fill="#f6f9fd",
            border="#d8e2ee",
            radius=16,
            shadow=False,
            cache_key="settings-tabs",
        )
        for group in SETTINGS_FIELD_GROUPS:
            button = self._primary_button(
                tabs,
                group,
                lambda name=group: self._show_settings_group(name),
                variant="soft" if group == self.active_settings_group else "secondary",
            )
            button.pack(side="left", padx=(0, 6), pady=2)
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
        row = self.tk.Frame(parent, bg=COLORS["card"], bd=0, highlightthickness=0)
        row.configure(height=COCKPIT_LAYOUT["setting_row_height"])
        row.grid_propagate(False)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)
        row.grid_rowconfigure(0, weight=1)
        label_stack = self.tk.Frame(row, bg=COLORS["card"])
        label_stack.grid(row=0, column=0, sticky="ew", padx=24, pady=16)
        self.tk.Label(label_stack, text=spec.label, bg=COLORS["card"], fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold"), justify="left", anchor="w", wraplength=420).pack(anchor="w")
        self.tk.Label(label_stack, text=SETTING_DESCRIPTIONS.get(spec.name, spec.name), bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), justify="left", anchor="w", wraplength=COCKPIT_LAYOUT["setting_description_wrap"]).pack(anchor="w", pady=(7, 0))

        if spec.kind == "bool":
            var = self.tk.BooleanVar(value=False)
            widget = self._toggle_control(row, var)
            widget.grid(row=0, column=1, sticky="e", padx=(20, 24), pady=30)
        else:
            var = self.tk.StringVar(value="")
            widget = self._entry_control(row, var, width=300)
            widget.grid(row=0, column=1, sticky="e", padx=(20, 24), pady=30)
        self.tk.Frame(row, bg="#e8eef6", height=1).grid(row=1, column=0, columnspan=2, sticky="ew", padx=24)
        self.form_vars[spec.name] = var
        return row

    def _build_field_group(self, parent: Any, field_names: List[str]) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        list_card = self.tk.Frame(parent, bg=COLORS["card"], bd=0, highlightthickness=0)
        list_card.grid(row=0, column=0, sticky="nsew")
        self._install_rounded_surface(
            list_card,
            fill=COLORS["card"],
            border="#e2e8f0",
            radius=COCKPIT_LAYOUT["card_radius"],
            shadow=False,
            cache_key=f"settings-list-{id(parent)}",
        )
        list_card.grid_rowconfigure(0, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        canvas = self.tk.Canvas(list_card, bg=COLORS["card"], bd=0, highlightthickness=0)
        scrollbar = self.tk.Scrollbar(list_card, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=18)
        inner = self.tk.Frame(canvas, bg=COLORS["card"])
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.grid_columnconfigure(0, weight=1)

        def sync_scroll_region(_event: Any | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_inner_width(event: Any) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", sync_scroll_region, add="+")
        canvas.bind("<Configure>", sync_inner_width, add="+")

        def on_mousewheel(event: Any) -> None:
            canvas.yview_scroll(int(-event.delta / 120), "units")

        def bind_scroll(_event: Any) -> None:
            canvas.bind_all("<MouseWheel>", on_mousewheel, add="+")

        def unbind_scroll(_event: Any) -> None:
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass

        list_card.bind("<Enter>", bind_scroll, add="+")
        list_card.bind("<Leave>", unbind_scroll, add="+")
        for row_index, name in enumerate(field_names):
            row = self._build_setting_row(inner, FIELD_SPEC_BY_NAME[name])
            row.grid(row=row_index, column=0, sticky="ew")

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

    def _run_workbench_action(self, key: str) -> None:
        if key == "optimize_only":
            self._start_optimize(sync_after=False)
            return
        if key == "optimize_sync":
            self._start_optimize(sync_after=True)
            return
        if key == "sync_only":
            self._start_sync_only()
            return
        if key == "proxy_test":
            self._start_proxy_test()
            return
        if key == "stop_task":
            self.runner.stop()
            return
        if key == "save_config":
            self._save_to_disk()
            return
        if key == "refresh_dashboard":
            self._refresh_dashboard()
            return
        if key == "open_output_folder":
            self._open_output_folder()
            return
        raise ValueError(f"unknown workbench action: {key}")

    def _show_page(self, key: str) -> None:
        self.active_page = key
        for page_key, frame in self.page_frames.items():
            if page_key == key:
                frame.tkraise()
            frame.grid(row=0, column=0, sticky="nsew")
        for item in NAV_ITEMS:
            button = self.nav_buttons[item.key]
            active = item.key == key
            fill = COLORS["blue_dark"] if active else COLORS["sidebar"]
            border = COLORS["blue_dark"] if active else COLORS["sidebar"]
            button._surface_fill = fill
            button._surface_border = border
            button._surface_shadow = bool(active)
            if hasattr(button, "_surface_redraw"):
                button._surface_redraw()
            body = getattr(button, "_nav_body", None)
            if body is not None:
                body.configure(bg=fill)
            icon = getattr(button, "_nav_icon", None)
            if icon is not None:
                image = self._badge_photo(
                    f"nav-{item.key}-{'active' if active else 'inactive'}",
                    NAV_ITEM_GLYPHS[item.key],
                    "#ffffff" if active else COLORS["muted"],
                    size=28,
                    background=fill,
                    border=fill,
                    text_color="#ffffff" if active else COLORS["muted"],
                )
                icon.configure(image=image, bg=fill)
                icon.image = image
            if active:
                self.page_title_var.set(PAGE_TITLES.get(item.key, item.label))
        for item in NAV_ITEMS:
            tab = self.page_tab_buttons.get(item.key)
            if tab is not None and hasattr(tab, "_set_tab_active"):
                tab._set_tab_active(item.key == key)
            elif tab is not None and hasattr(tab, "_set_button_variant"):
                tab._set_button_variant("soft" if item.key == key else "ghost")
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
            variant = "soft" if active else "secondary"
            if hasattr(button, "_set_button_variant"):
                button._set_button_variant(variant)
            else:
                style = BUTTON_VARIANTS[variant]
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
        self.port_share_var.set(output_card.detail)
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
        keep = int(self.config_data.get("OUTPUT_BACKUP_KEEP", 20) or 20)
        self.backup_detail_var.set(f"保留 {keep} 份")
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
