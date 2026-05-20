from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import desktop_app


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"


def _resolve_path(raw_path: str | Path | None, base: Path = ROOT) -> Path:
    if raw_path is None:
        return base
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return base / path


def _format_dt(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp).isoformat(timespec="seconds")


def _read_output_lines(config: Dict[str, Any]) -> list[str]:
    output_path = _resolve_path(config.get("OUTPUT_FILE", "ip.txt"))
    if not output_path.exists():
        return []
    return output_path.read_text(encoding="utf-8").splitlines()


def _build_backups(config: Dict[str, Any]) -> list[dict[str, Any]]:
    backups = []
    for path in desktop_app.list_output_backups(CONFIG_PATH, config):
        stat = path.stat()
        backups.append(
            {
                "name": path.name,
                "path": str(path),
                "modified_at": _format_dt(stat.st_mtime),
                "size": stat.st_size,
            }
        )
    return backups


def build_state() -> dict[str, Any]:
    config = desktop_app.load_config_file(CONFIG_PATH)
    output_lines = _read_output_lines(config)
    output_path = _resolve_path(config.get("OUTPUT_FILE", "ip.txt"))
    output_stat = output_path.stat() if output_path.exists() else None

    with redirect_stdout(io.StringIO()):
        preflight = desktop_app.build_preflight_report(
            config_path=CONFIG_PATH,
            config=config,
            python_exe=sys.executable,
            mode_label="工作台检查",
            environ=os.environ,
        )
        cards = desktop_app.build_workbench_status_cards(
            CONFIG_PATH,
            config,
            environ=os.environ,
        )

    common_values = desktop_app.extract_common_field_values(config)

    return {
        "config_path": str(CONFIG_PATH),
        "python_exe": sys.executable,
        "config": config,
        "common_values": common_values,
        "field_specs": [asdict(spec) for spec in desktop_app.FIELD_SPECS],
        "field_groups": desktop_app.SETTINGS_FIELD_GROUPS,
        "output_path": str(output_path),
        "output_exists": output_path.exists(),
        "output_updated_at": _format_dt(output_stat.st_mtime) if output_stat else None,
        "output_count": len(output_lines),
        "output_preview": output_lines[:20],
        "port_share": desktop_app.calculate_port_share(output_lines),
        "backups": _build_backups(config),
        "preflight": asdict(preflight),
        "cards": [asdict(card) for card in cards],
    }


def save_config_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    config = desktop_app.load_config_file(CONFIG_PATH)
    mode = payload.get("mode", "common")
    if mode == "raw":
        raw_config = payload.get("config")
        if not isinstance(raw_config, dict):
            raise ValueError("raw mode requires a config object")
        desktop_app.save_config_file(raw_config, CONFIG_PATH)
        return raw_config

    values = payload.get("values")
    if not isinstance(values, dict):
        raise ValueError("common mode requires values")
    updated = desktop_app.apply_common_field_values(config, values)
    desktop_app.save_config_file(updated, CONFIG_PATH)
    return updated


def restore_backup(backup_path: str) -> dict[str, Any]:
    config = desktop_app.load_config_file(CONFIG_PATH)
    restored = desktop_app.restore_output_backup(
        _resolve_path(backup_path),
        CONFIG_PATH,
        config,
    )
    return {
        "restored_path": str(restored),
    }


def test_proxy(proxy_url: str | None) -> dict[str, Any]:
    if not proxy_url:
        return {
            "ok": False,
            "proxy_url": "",
            "message": "未配置 GITHUB_SYNC_PROXY_URL",
        }

    import urllib.request

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    )
    try:
        with opener.open("https://github.com", timeout=10) as response:
            response.read(64)
        return {
            "ok": True,
            "proxy_url": proxy_url,
            "message": "github.com 代理连通",
        }
    except Exception as exc:  # pragma: no cover - surfaced in UI
        return {
            "ok": False,
            "proxy_url": proxy_url,
            "message": str(exc),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cfnb desktop bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("state")

    save_parser = sub.add_parser("save-config")
    save_parser.add_argument("--mode", choices=["common", "raw"], default="common")

    restore_parser = sub.add_parser("restore-backup")
    restore_parser.add_argument("backup_path")

    proxy_parser = sub.add_parser("test-proxy")
    proxy_parser.add_argument("--proxy-url", default="")

    args = parser.parse_args(argv)

    if args.command == "state":
        payload = build_state()
    elif args.command == "save-config":
        payload_raw = os.environ.get("CFNB_UI_PAYLOAD", "")
        if not payload_raw:
            raise SystemExit("CFNB_UI_PAYLOAD is required")
        payload = json.loads(payload_raw)
        payload["mode"] = args.mode
        payload = {"saved": save_config_from_payload(payload)}
    elif args.command == "restore-backup":
        payload = restore_backup(args.backup_path)
    elif args.command == "test-proxy":
        payload = test_proxy(args.proxy_url)
    else:  # pragma: no cover - argparse enforces commands
        raise SystemExit(1)

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
