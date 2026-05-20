import json
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
