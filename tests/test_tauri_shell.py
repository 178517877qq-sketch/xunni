import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TauriShellTests(unittest.TestCase):
    def test_package_uses_cockpit_tools_style_stack(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual("cfnb-tauri-desktop", package["name"])
        self.assertIn("tauri", package["scripts"])
        self.assertIn("@vitejs/plugin-react", package["devDependencies"])
        self.assertIn("vite", package["devDependencies"])
        self.assertIn("tailwindcss", package["devDependencies"])
        self.assertIn("daisyui", package["devDependencies"])
        self.assertIn("@tauri-apps/api", package["dependencies"])
        self.assertIn("@tauri-apps/plugin-shell", package["dependencies"])
        self.assertIn("react", package["dependencies"])
        self.assertIn("react-dom", package["dependencies"])

    def test_tauri_window_matches_reference_desktop_shell(self):
        config = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
        window = config["app"]["windows"][0]

        self.assertEqual("cfnb 手动优选工具", config["productName"])
        self.assertEqual(1280, window["width"])
        self.assertEqual(800, window["height"])
        self.assertTrue(window["resizable"])
        self.assertEqual("../dist", config["build"]["frontendDist"])

    def test_frontend_maps_manual_workflow_to_existing_python_cli(self):
        workflow = (ROOT / "src" / "lib" / "workflow.ts").read_text(encoding="utf-8")

        self.assertIn("--no-github-sync", workflow)
        self.assertIn("--sync-only", workflow)
        self.assertIn("main.py", workflow)
        self.assertIn("github.com", workflow)
        self.assertIn("Command.create", workflow)

    def test_react_app_contains_cockpit_dashboard_surfaces(self):
        app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        for label in ["只运行优选", "优选后自动上传", "上传到 GitHub", "测试 GitHub 代理"]:
            self.assertIn(label, app)
        self.assertIn("glass-panel", app)
        self.assertIn("sidebar-rail", app)
        self.assertIn("rounded-[32px]", app)
        self.assertIn("box-shadow", css)
        self.assertIn("linear-gradient", css)


if __name__ == "__main__":
    unittest.main()
