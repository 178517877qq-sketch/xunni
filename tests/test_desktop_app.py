import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import desktop_app


class DesktopAppHelperTests(unittest.TestCase):
    def test_apply_common_field_values_round_trips_editable_lists_and_numbers(self):
        config = {
            "USE_GLOBAL_MODE": False,
            "GLOBAL_TOP_N": 24,
            "PER_COUNTRY_TOP_N": 5,
            "BANDWIDTH_CANDIDATES": 500,
            "OUTPUT_NODE_LIMIT": 20,
            "TEST_AVAILABILITY": True,
            "STABILITY_SCORING_ENABLED": True,
            "ENABLE_CF_OFFICIAL_IP_SAMPLING": True,
            "CF_OFFICIAL_SAMPLE_PER_24": 3,
            "CF_OFFICIAL_SAMPLE_PORTS": [443, 2053],
            "LOCAL_SEED_FILES": ["重要ip.txt", "全量ip.txt"],
            "FILTER_COUNTRIES_ENABLED": True,
            "ALLOWED_COUNTRIES": ["US", "JP"],
            "GITHUB_SYNC_ENABLED": True,
            "GITHUB_SYNC_PROXY_URL": "http://127.0.0.1:7890",
            "CF_ENABLED": False,
            "DNS_UPDATE_TARGET_COUNT": 15,
            "ENABLE_WXPUSHER": True,
            "GITHUB_SYNC_MAX_RETRIES": 3,
            "FILTER_BLOCKED_COUNTRIES_ENABLED": True,
            "_comment": "keep-me",
        }

        values = desktop_app.extract_common_field_values(config)

        self.assertFalse(values["USE_GLOBAL_MODE"])
        self.assertEqual(values["CF_OFFICIAL_SAMPLE_PORTS"], "443, 2053")
        self.assertEqual(values["LOCAL_SEED_FILES"], "重要ip.txt, 全量ip.txt")
        self.assertTrue(values["GITHUB_SYNC_ENABLED"])
        self.assertEqual(values["GITHUB_SYNC_PROXY_URL"], "http://127.0.0.1:7890")

        updated = desktop_app.apply_common_field_values(
            config,
            {
                **values,
                "USE_GLOBAL_MODE": True,
                "GLOBAL_TOP_N": "18",
                "CF_OFFICIAL_SAMPLE_PORTS": "443, 8443",
                "LOCAL_SEED_FILES": "seed-a.txt, seed-b.txt",
                "ALLOWED_COUNTRIES": "US, JP, SG",
                "GITHUB_SYNC_ENABLED": False,
                "GITHUB_SYNC_PROXY_URL": "socks5://127.0.0.1:1080",
            },
        )

        self.assertTrue(updated["USE_GLOBAL_MODE"])
        self.assertEqual(updated["GLOBAL_TOP_N"], 18)
        self.assertEqual(updated["CF_OFFICIAL_SAMPLE_PORTS"], [443, 8443])
        self.assertEqual(updated["LOCAL_SEED_FILES"], ["seed-a.txt", "seed-b.txt"])
        self.assertEqual(updated["ALLOWED_COUNTRIES"], ["US", "JP", "SG"])
        self.assertFalse(updated["GITHUB_SYNC_ENABLED"])
        self.assertEqual(updated["GITHUB_SYNC_PROXY_URL"], "socks5://127.0.0.1:1080")
        self.assertEqual(updated["_comment"], "keep-me")

    def test_save_config_file_preserves_existing_comment_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            path.write_text(
                '{"_comment":"keep","USE_GLOBAL_MODE":false,"GLOBAL_TOP_N":24}',
                encoding="utf-8",
            )

            config = desktop_app.load_config_file(path)
            config["GLOBAL_TOP_N"] = 30
            desktop_app.save_config_file(config, path)

            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved["_comment"], "keep")
        self.assertEqual(saved["GLOBAL_TOP_N"], 30)

    def test_build_run_command_uses_unbuffered_python_and_main_script(self):
        cmd = desktop_app.build_run_command(r"C:\\Python\\python.exe", r"C:\\repo\\main.py")

        self.assertEqual([r"C:\\Python\\python.exe", "-u", r"C:\\repo\\main.py"], cmd)

    def test_desktop_commands_support_optimize_sync_and_proxy_test_modes(self):
        python_exe = r"C:\\Python\\python.exe"
        main_script = r"C:\\repo\\main.py"

        self.assertEqual(
            [python_exe, "-u", main_script, "--no-github-sync"],
            desktop_app.build_optimize_command(python_exe, main_script, sync_after=False),
        )
        self.assertEqual(
            [python_exe, "-u", main_script],
            desktop_app.build_optimize_command(python_exe, main_script, sync_after=True),
        )
        self.assertEqual(
            [python_exe, "-u", main_script, "--sync-only"],
            desktop_app.build_sync_only_command(python_exe, main_script),
        )

        proxy_cmd = desktop_app.build_proxy_test_command(python_exe, "http://127.0.0.1:7890")

        self.assertEqual(python_exe, proxy_cmd[0])
        self.assertEqual("-c", proxy_cmd[1])
        self.assertIn("github.com", proxy_cmd[2])
        self.assertEqual("http://127.0.0.1:7890", proxy_cmd[3])

    def test_preflight_report_warns_about_proxy_environment_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.json"
            config_path.write_text("{}", encoding="utf-8")

            report = desktop_app.build_preflight_report(
                config_path=config_path,
                config={"OUTPUT_FILE": "ip.txt", "GITHUB_SYNC_PROXY_URL": "http://127.0.0.1:7890"},
                python_exe=sys.executable,
                mode_label="只运行优选",
                environ={"HTTPS_PROXY": "http://127.0.0.1:7890"},
            )

        self.assertTrue(report.can_continue)
        self.assertTrue(report.has_warnings)
        self.assertIn("断开 VPN", report.text)
        self.assertIn("HTTPS_PROXY", report.text)


    def test_sidebar_and_settings_sections_match_designed_workspace_layout(self):
        self.assertEqual(
            ["workbench", "results", "settings", "logs"],
            [item.key for item in desktop_app.NAV_ITEMS],
        )
        self.assertEqual(["常用", "源池", "同步", "高级"], list(desktop_app.SETTINGS_FIELD_GROUPS))

    def test_list_output_backups_filters_and_sorts_latest_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.json"
            backup_dir = root / "backups"
            backup_dir.mkdir()
            config = {"OUTPUT_FILE": "ip.txt", "OUTPUT_BACKUP_DIR": "backups"}

            first = backup_dir / "ip.txt.20260101-000000.bak"
            second = backup_dir / "ip.txt.20260102-000000.bak"
            ignored = backup_dir / "other.txt.20260103-000000.bak"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            ignored.write_text("ignored", encoding="utf-8")
            os.utime(first, (1, 1))
            os.utime(second, (2, 2))
            os.utime(ignored, (3, 3))

            backups = desktop_app.list_output_backups(config_path, config)

        self.assertEqual([second, first], backups)

    def test_restore_output_backup_backs_up_current_output_before_copying_selected_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.json"
            output = root / "ip.txt"
            backup_dir = root / "backups"
            selected_backup = backup_dir / "ip.txt.20260102-000000.bak"
            backup_dir.mkdir()
            output.write_text("current\n", encoding="utf-8")
            selected_backup.write_text("restored\n", encoding="utf-8")
            backup_callback = Mock(return_value=backup_dir / "ip.txt.before-restore.bak")

            restored_path = desktop_app.restore_output_backup(
                selected_backup,
                config_path,
                {
                    "OUTPUT_FILE": "ip.txt",
                    "OUTPUT_BACKUP_DIR": "backups",
                    "OUTPUT_BACKUP_KEEP": 20,
                },
                backup_callback=backup_callback,
            )

            restored = output.read_text(encoding="utf-8")

        self.assertEqual(output, restored_path)
        self.assertEqual("restored\n", restored)
        backup_callback.assert_called_once_with(output, backup_dir, 20)

    def test_calculate_port_share_counts_443_nodes(self):
        self.assertEqual(
            "67%",
            desktop_app.calculate_port_share([
                "1.1.1.1:443#US",
                "1.1.1.2:2053#US",
                "1.1.1.3:443#JP",
            ]),
        )

    def test_action_button_variants_define_clear_visual_hierarchy(self):
        self.assertEqual("#2563eb", desktop_app.BUTTON_VARIANTS["primary"]["bg"])
        self.assertEqual("#dc2626", desktop_app.BUTTON_VARIANTS["danger"]["bg"])
        self.assertEqual("#ffffff", desktop_app.BUTTON_VARIANTS["secondary"]["bg"])
        self.assertEqual("#dbeafe", desktop_app.BUTTON_VARIANTS["soft"]["bg"])

    def test_top_toolbar_actions_match_manual_workflow(self):
        self.assertEqual(
            ["refresh_dashboard", "save_config", "open_output_folder"],
            [action.key for action in desktop_app.APP_TOOLBAR_ACTIONS],
        )
        self.assertEqual(
            ["刷新检查", "保存配置", "输出目录"],
            [action.label for action in desktop_app.APP_TOOLBAR_ACTIONS],
        )
        self.assertEqual(
            ["ghost", "secondary", "soft"],
            [action.variant for action in desktop_app.APP_TOOLBAR_ACTIONS],
        )

    def test_workbench_actions_match_cockpit_style_quick_tiles(self):
        self.assertEqual(
            ["optimize_only", "optimize_sync", "sync_only", "proxy_test", "stop_task", "save_config", "refresh_dashboard", "open_output_folder"],
            [action.key for action in desktop_app.WORKBENCH_ACTIONS],
        )
        self.assertEqual(
            ["RUN", "AUTO", "GH", "TEST", "STOP", "SAVE", "REF", "DIR"],
            [action.icon for action in desktop_app.WORKBENCH_ACTIONS],
        )
        self.assertEqual(
            ["只运行优选", "优选后自动上传", "上传到 GitHub", "测试 GitHub 代理", "停止任务", "保存设置", "刷新状态", "输出目录"],
            [action.label for action in desktop_app.WORKBENCH_ACTIONS],
        )

    def test_workbench_actions_split_into_main_task_and_compact_tools(self):
        self.assertEqual(
            ["optimize_only", "optimize_sync", "sync_only", "proxy_test"],
            desktop_app.WORKBENCH_PRIMARY_ACTIONS,
        )
        self.assertEqual(
            ["stop_task", "save_config", "refresh_dashboard", "open_output_folder"],
            desktop_app.WORKBENCH_SECONDARY_ACTIONS,
        )

    def test_desktop_app_defaults_to_modern_react_route(self):
        self.assertFalse(desktop_app.should_use_legacy_tk(argv=[], environ={}))
        self.assertTrue(desktop_app.should_use_legacy_tk(argv=["--legacy-tk"], environ={}))
        self.assertTrue(desktop_app.should_use_legacy_tk(argv=[], environ={"CFNB_LEGACY_TK": "1"}))

    def test_modern_desktop_strategy_prefers_tauri_when_rust_exists(self):
        def fake_which(name):
            return f"C:/tools/{name}" if name in {"npm.cmd", "cargo", "rustc"} else None

        strategy = desktop_app.resolve_modern_desktop_strategy(which=fake_which)

        self.assertEqual("tauri", strategy.kind)
        self.assertEqual(["C:/tools/npm.cmd", "run", "tauri", "dev"], strategy.command)

    def test_modern_desktop_strategy_falls_back_to_web_app_without_rust(self):
        def fake_which(name):
            return f"C:/tools/{name}" if name == "npm.cmd" else None

        strategy = desktop_app.resolve_modern_desktop_strategy(which=fake_which)

        self.assertEqual("web-app", strategy.kind)
        self.assertIn("dev", strategy.command)
        self.assertIn("--port", strategy.command)
        self.assertEqual(desktop_app.MODERN_DESKTOP_URL, strategy.url)

    def test_cockpit_layout_tokens_prevent_square_blocks_and_text_clipping(self):
        layout = desktop_app.COCKPIT_LAYOUT

        self.assertGreaterEqual(layout["card_radius"], 26)
        self.assertGreaterEqual(layout["main_task_height"], 220)
        self.assertGreaterEqual(layout["action_tile_height"], 92)
        self.assertLessEqual(layout["action_text_wrap"], 160)
        self.assertLessEqual(layout["action_hint_wrap"], 160)
        self.assertGreaterEqual(layout["setting_row_height"], 96)
        self.assertGreaterEqual(layout["setting_description_wrap"], 560)

    def test_page_tab_style_uses_blue_active_pill_and_rounded_hover_shadow(self):
        style = desktop_app.PAGE_TAB_STYLE

        self.assertEqual("#dbeafe", style["active_fill"])
        self.assertEqual("#1d4ed8", style["active_text"])
        self.assertTrue(style["inactive_transparent"])
        self.assertGreaterEqual(style["radius"], 18)
        self.assertGreaterEqual(style["hover_shadow_alpha"], 30)

        inactive_image = desktop_app.render_page_tab_image(
            width=128,
            height=42,
            active=False,
            hover=False,
        )
        self.assertEqual((128, 42), inactive_image.size)
        self.assertEqual(0, inactive_image.getpixel((64, 21))[3])

        image = desktop_app.render_page_tab_image(
            width=128,
            height=42,
            active=False,
            hover=True,
        )
        self.assertEqual((128, 42), image.size)
        self.assertLessEqual(image.getpixel((0, 0))[3], 8)
        self.assertGreater(image.getpixel((64, 21))[3], 0)

    def test_page_tabs_use_drawn_line_icons_instead_of_text_glyphs(self):
        self.assertEqual(
            ["workbench", "results", "settings", "logs"],
            list(desktop_app.PAGE_TAB_ICONS),
        )
        self.assertNotIn("Run", desktop_app.PAGE_TAB_ICONS.values())
        self.assertNotIn("IP", desktop_app.PAGE_TAB_ICONS.values())

        icon = desktop_app.render_nav_icon_image("workbench", "#1d4ed8")
        self.assertEqual((18, 18), icon.size)
        self.assertEqual("RGBA", icon.mode)
        self.assertGreater(icon.getchannel("A").getextrema()[1], 0)

    def test_cockpit_theme_uses_gradient_background_and_translucent_surfaces(self):
        theme = desktop_app.COCKPIT_THEME

        self.assertEqual("#eef4f8", theme["background_base"])
        self.assertTrue(theme["card_fill"].endswith("dd"))
        self.assertTrue(theme["panel_fill"].endswith("e8"))
        self.assertGreaterEqual(theme["surface_shadow_blur"], 16)
        self.assertGreaterEqual(theme["surface_shadow_blur"], 24)
        self.assertEqual((0, 8), theme["surface_shadow_offset"])
        self.assertGreaterEqual(theme["surface_shadow_margin"], 8)

        background = desktop_app.render_cockpit_background(160, 90)
        self.assertEqual((160, 90), background.size)
        self.assertEqual("RGBA", background.mode)
        self.assertNotEqual(background.getpixel((8, 8)), background.getpixel((150, 80)))

        surface = desktop_app.render_rounded_surface(
            120,
            72,
            theme["card_fill"],
            theme["card_border"],
            radius=theme["card_radius"],
            shadow=True,
            shadow_alpha=theme["surface_shadow_alpha"],
            shadow_blur=theme["surface_shadow_blur"],
        )
        center_alpha = surface.getpixel((60, 36))[3]
        self.assertGreater(center_alpha, 190)
        self.assertLess(center_alpha, 255)
        self.assertLessEqual(surface.getpixel((0, 0))[3], 8)

    def test_render_rounded_surface_can_inset_shadow_to_avoid_square_edges(self):
        image = desktop_app.render_rounded_surface(
            160,
            90,
            "#ffffffdd",
            "#ffffffcc",
            radius=28,
            shadow=True,
            shadow_alpha=30,
            shadow_offset=(0, 8),
            shadow_blur=24,
            shadow_margin=12,
        )
        alpha = image.getchannel("A")
        w, h = image.size
        edge_alpha = []
        for x in range(w):
            edge_alpha.append(alpha.getpixel((x, 0)))
            edge_alpha.append(alpha.getpixel((x, h - 1)))
        for y in range(h):
            edge_alpha.append(alpha.getpixel((0, y)))
            edge_alpha.append(alpha.getpixel((w - 1, y)))

        self.assertLessEqual(max(edge_alpha), 5)
        self.assertLessEqual(image.getpixel((4, h // 2))[3], 5)
        self.assertGreater(image.getpixel((18, h // 2))[3], 0)
        self.assertGreater(image.getpixel((w // 2, h // 2))[3], 190)

    def test_workbench_layout_prioritizes_one_main_task_and_status_summary(self):
        self.assertEqual(
            ["main_task", "latest_result"],
            desktop_app.COCKPIT_WORKBENCH_LAYOUT["left"],
        )
        self.assertEqual(
            ["status_summary", "preflight", "activity_log"],
            desktop_app.COCKPIT_WORKBENCH_LAYOUT["right"],
        )

    def test_cockpit_structure_matches_reference_spacing(self):
        structure = desktop_app.COCKPIT_STRUCTURE

        self.assertGreaterEqual(structure["window_height"], 900)
        self.assertGreaterEqual(structure["main_top_padding"], 50)
        self.assertEqual(["header", "tabs", "toolbar", "content"], structure["main_rows"])
        self.assertGreaterEqual(structure["toolbar_height"], 62)
        self.assertLessEqual(structure["sidebar_rail_height"], 560)
        self.assertTrue(structure["sidebar_has_action_button"])
        self.assertEqual(["shell"], structure["background_layers"])

    def test_render_badge_image_returns_square_rgba_asset(self):
        image = desktop_app.render_badge_image("RUN", "#2563eb")

        self.assertEqual((40, 40), image.size)
        self.assertEqual("RGBA", image.mode)

    def test_render_rounded_surface_keeps_corners_transparent(self):
        image = desktop_app.render_rounded_surface(80, 50, "#ffffff", "#d8e1ec")

        self.assertEqual((80, 50), image.size)
        self.assertLessEqual(image.getpixel((0, 0))[3], 5)
        self.assertGreater(image.getpixel((40, 25))[3], 0)

    def test_split_setting_fields_for_columns_keeps_row_style_columns_balanced(self):
        self.assertEqual(
            [["A", "C", "E"], ["B", "D"]],
            desktop_app.split_setting_fields_for_columns(["A", "B", "C", "D", "E"], columns=2),
        )

    def test_build_workbench_status_cards_summarizes_runtime_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.json"
            output = root / "ip.txt"
            output.write_text("1.1.1.1:443#US\n1.1.1.2:2053#JP\n", encoding="utf-8")

            cards = desktop_app.build_workbench_status_cards(
                config_path,
                {"OUTPUT_FILE": "ip.txt", "GITHUB_SYNC_PROXY_URL": "http://127.0.0.1:7890"},
                environ={"HTTPS_PROXY": "http://127.0.0.1:7890"},
            )

        self.assertEqual(["VPN/代理提醒", "当前 ip.txt", "GitHub 上传"], [card.title for card in cards])
        self.assertEqual(["VPN", "IP", "GH"], [card.icon for card in cards])
        self.assertEqual("检测到代理变量", cards[0].value)
        self.assertEqual("2", cards[1].value)
        self.assertEqual("50%", cards[1].detail)
        self.assertEqual("代理已配置", cards[2].value)

    def test_build_restore_confirmation_message_mentions_protective_backup(self):
        message = desktop_app.build_restore_confirmation_message(Path("ip.txt.20260101-000000.bak"))

        self.assertIn("恢复前会先备份当前 ip.txt", message)
        self.assertIn("ip.txt.20260101-000000.bak", message)


if __name__ == "__main__":
    unittest.main()
