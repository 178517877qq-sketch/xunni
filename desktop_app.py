from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("config.json")
MAIN_SCRIPT_PATH = Path(__file__).resolve().with_name("main.py")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str
    section: str


FIELD_SPECS: List[FieldSpec] = [
    FieldSpec("USE_GLOBAL_MODE", "全局模式", "bool", "基础"),
    FieldSpec("GLOBAL_TOP_N", "全局 TopN", "int", "基础"),
    FieldSpec("PER_COUNTRY_TOP_N", "分国家 TopN", "int", "基础"),
    FieldSpec("BANDWIDTH_CANDIDATES", "带宽候选数", "int", "基础"),
    FieldSpec("OUTPUT_NODE_LIMIT", "输出节点上限", "int", "基础"),
    FieldSpec("MIN_SUCCESS_RATE", "TCP 最低成功率", "float", "基础"),
    FieldSpec("TIMEOUT", "TCP 超时", "float", "基础"),
    FieldSpec("TCP_PROBES", "TCP 探测次数", "int", "基础"),
    FieldSpec("BANDWIDTH_SIZE_MB", "测速大小(MB)", "float", "基础"),
    FieldSpec("TEST_AVAILABILITY", "启用可用性检测", "bool", "基础"),
    FieldSpec("STABILITY_SCORING_ENABLED", "启用稳定性评分", "bool", "基础"),
    FieldSpec("FILTER_COUNTRIES_ENABLED", "启用国家过滤", "bool", "基础"),
    FieldSpec("ENABLE_CF_OFFICIAL_IP_SAMPLING", "启用官方 IP 采样", "bool", "源与筛选"),
    FieldSpec("CF_OFFICIAL_SAMPLE_PER_24", "每个 /24 采样数", "int", "源与筛选"),
    FieldSpec("CF_OFFICIAL_SAMPLE_PORTS", "官方采样端口", "csv_int", "源与筛选"),
    FieldSpec("LOCAL_SEED_FILES", "本地种子文件", "csv_str", "源与筛选"),
    FieldSpec("ALLOWED_COUNTRIES", "允许国家", "csv_str", "源与筛选"),
    FieldSpec("FILTER_BLOCKED_COUNTRIES_ENABLED", "屏蔽国家过滤", "bool", "源与筛选"),
    FieldSpec("BLOCKED_COUNTRIES", "屏蔽国家列表", "csv_str", "源与筛选"),
    FieldSpec("OUTPUT_FILE", "输出文件", "str", "通知与同步"),
    FieldSpec("STABILITY_STATS_FILE", "稳定性统计文件", "str", "通知与同步"),
    FieldSpec("LOG_FILE", "日志文件", "str", "通知与同步"),
    FieldSpec("CF_ENABLED", "启用 Cloudflare DNS", "bool", "通知与同步"),
    FieldSpec("DNS_UPDATE_TARGET_COUNT", "DNS 更新数量", "int", "通知与同步"),
    FieldSpec("ENABLE_WXPUSHER", "启用 WxPusher", "bool", "通知与同步"),
    FieldSpec("GITHUB_SYNC_ENABLED", "自动同步 GitHub", "bool", "通知与同步"),
    FieldSpec("GITHUB_SYNC_PROXY_URL", "GitHub 同步代理", "str", "通知与同步"),
    FieldSpec("GITHUB_SYNC_MAX_RETRIES", "GitHub 重试次数", "int", "通知与同步"),
    FieldSpec("ENABLE_LOGGING", "启用运行日志", "bool", "通知与同步"),
    FieldSpec("MAX_WORKERS", "TCP 并发线程", "int", "高级"),
    FieldSpec("AVAILABILITY_WORKERS", "可用性线程", "int", "高级"),
    FieldSpec("BANDWIDTH_WORKERS", "带宽线程", "int", "高级"),
    FieldSpec("AVAILABILITY_RETRY_MAX", "可用性重试", "int", "高级"),
    FieldSpec("BANDWIDTH_RETRY_MAX", "带宽重试", "int", "高级"),
    FieldSpec("CF_OFFICIAL_COUNTRY_CODE", "官方采样国家码", "str", "高级"),
    FieldSpec("CF_DNS_RECORD_NAME", "Cloudflare 记录名", "str", "高级"),
]


def load_config_file(path: Path | str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config_file(config: Mapping[str, Any], path: Path | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(config), f, ensure_ascii=False, indent=4)
        f.write("\n")


def build_run_command(python_exe: str, main_script: str) -> List[str]:
    return [python_exe, "-u", main_script]


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
        if self.running():
            raise RuntimeError("process already running")

        command = build_run_command(python_exe, str(MAIN_SCRIPT_PATH))
        env = dict(**__import__("os").environ)
        env["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            command,
            cwd=str(MAIN_SCRIPT_PATH.parent),
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
        self.root.minsize(1100, 760)

        self.runner = ProcessRunner()
        self.config_path_var = tk.StringVar(value=str(DEFAULT_CONFIG_PATH))
        self.status_var = tk.StringVar(value="准备就绪")
        self.python_var = tk.StringVar(value=sys.executable)
        self.config_data: Dict[str, Any] = {}
        self.form_vars: Dict[str, Any] = {}
        self.raw_text = None
        self.log_text = None
        self.result_list = None
        self.result_count_var = tk.StringVar(value="结果: 0")
        self.output_file_var = tk.StringVar(value="")

        self._build_ui()
        self._load_from_disk()
        self._poll_runner_queue()

    def _build_ui(self) -> None:
        ttk = self.ttk
        tk = self.tk

        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="配置文件").grid(row=0, column=0, sticky="w")
        config_entry = ttk.Entry(top, textvariable=self.config_path_var, width=70)
        config_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(top, text="浏览", command=self._browse_config).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(top, text="加载", command=self._load_from_disk).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(top, text="保存", command=self._save_to_disk).grid(row=0, column=4, padx=(0, 8))
        ttk.Label(top, text="Python").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.python_var, width=70).grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(8, 0))
        ttk.Label(top, textvariable=self.status_var).grid(row=1, column=2, columnspan=3, sticky="w", pady=(8, 0))
        top.columnconfigure(1, weight=1)

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        form_host = ttk.Frame(body)
        side_host = ttk.Frame(body)
        body.add(form_host, weight=3)
        body.add(side_host, weight=2)

        form_notebook = ttk.Notebook(form_host)
        form_notebook.pack(fill="both", expand=True)

        for section in ("基础", "源与筛选", "通知与同步", "高级"):
            frame = ttk.Frame(form_notebook, padding=10)
            form_notebook.add(frame, text=section)
            self._build_field_section(frame, section)

        raw_frame = ttk.Frame(form_notebook, padding=10)
        form_notebook.add(raw_frame, text="完整配置")
        self.raw_text = self.scrolledtext.ScrolledText(raw_frame, wrap="none", height=20, undo=True)
        self.raw_text.pack(fill="both", expand=True)

        raw_buttons = ttk.Frame(raw_frame)
        raw_buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(raw_buttons, text="应用原始 JSON", command=self._apply_raw_to_form).pack(side="left")
        ttk.Button(raw_buttons, text="从表单刷新原始 JSON", command=self._refresh_raw_from_form).pack(side="left", padx=(8, 0))

        side_notebook = ttk.Notebook(side_host)
        side_notebook.pack(fill="both", expand=True)

        log_frame = ttk.Frame(side_notebook, padding=10)
        side_notebook.add(log_frame, text="日志")
        self.log_text = self.scrolledtext.ScrolledText(log_frame, wrap="word", height=20, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        result_frame = ttk.Frame(side_notebook, padding=10)
        side_notebook.add(result_frame, text="结果")
        ttk.Label(result_frame, textvariable=self.result_count_var).pack(anchor="w")
        self.result_list = tk.Listbox(result_frame, height=18)
        self.result_list.pack(fill="both", expand=True, pady=(8, 8))

        result_buttons = ttk.Frame(result_frame)
        result_buttons.pack(fill="x")
        ttk.Button(result_buttons, text="刷新结果", command=self._refresh_results).pack(side="left")
        ttk.Button(result_buttons, text="打开输出目录", command=self._open_output_folder).pack(side="left", padx=(8, 0))

        footer = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        footer.pack(fill="x")
        ttk.Button(footer, text="开始运行", command=self._start_run).pack(side="left")
        ttk.Button(footer, text="停止", command=self.runner.stop).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="同步表单到配置", command=self._sync_form_to_config).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="保存并运行", command=self._save_and_run).pack(side="left", padx=(8, 0))

    def _build_field_section(self, parent: Any, section: str) -> None:
        ttk = self.ttk
        fields = [spec for spec in FIELD_SPECS if spec.section == section]
        for index, spec in enumerate(fields):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(parent, text=spec.label).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=(0, 8))
            if spec.kind == "bool":
                var = self.tk.BooleanVar(value=False)
                widget = ttk.Checkbutton(parent, variable=var)
            else:
                var = self.tk.StringVar(value="")
                widget = ttk.Entry(parent, textvariable=var, width=36)
            widget.grid(row=row, column=col + 1, sticky="ew", pady=(0, 8))
            self.form_vars[spec.name] = var
        for col in range(4):
            parent.columnconfigure(col, weight=1 if col % 2 == 1 else 0)

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
        self.status_var.set(f"已加载配置: {path}")
        self._refresh_raw_from_form()
        self._refresh_results()

    def _save_to_disk(self) -> None:
        try:
            self._sync_form_to_config()
            save_config_file(self.config_data, Path(self.config_path_var.get()).expanduser())
        except Exception as exc:
            self.messagebox.showerror("保存失败", f"无法保存配置文件：{exc}")
            return
        self.status_var.set(f"已保存配置: {self.config_path_var.get()}")

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

    def _append_log(self, line: str) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert(self.tk.END, line + "\n")
        self.log_text.see(self.tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        if self.log_text is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", self.tk.END)
        self.log_text.configure(state="disabled")

    def _start_run(self) -> None:
        if self.runner.running():
            self.messagebox.showinfo("运行中", "当前已有任务在运行。")
            return
        self._save_to_disk()
        self._clear_log()
        try:
            self.runner.start(self.python_var.get().strip() or sys.executable, Path(self.config_path_var.get()).expanduser())
        except Exception as exc:
            self.messagebox.showerror("启动失败", f"无法启动任务：{exc}")
            return
        self.status_var.set("运行中")

    def _save_and_run(self) -> None:
        self._save_to_disk()
        self._start_run()

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
                self._refresh_results()
        self.root.after(100, self._poll_runner_queue)

    def _refresh_results(self) -> None:
        if self.result_list is None:
            return
        output_file = Path(self.config_data.get("OUTPUT_FILE", "ip.txt"))
        if not output_file.is_absolute():
            output_file = Path(self.config_path_var.get()).expanduser().parent / output_file
        self.output_file_var.set(str(output_file))
        self.result_list.delete(0, self.tk.END)
        if not output_file.exists():
            self.result_count_var.set("结果: 0")
            return
        try:
            lines = [line.strip() for line in output_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as exc:
            self.result_count_var.set("结果: 0")
            self._append_log(f"[结果] 无法读取输出文件: {exc}")
            return
        for line in lines:
            self.result_list.insert(self.tk.END, line)
        self.result_count_var.set(f"结果: {len(lines)}")

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
