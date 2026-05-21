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
        self.assertEqual("main", window["label"])
        self.assertEqual(1280, window["width"])
        self.assertEqual(800, window["height"])
        self.assertEqual(900, window["minWidth"])
        self.assertEqual(600, window["minHeight"])
        self.assertEqual("Overlay", window["titleBarStyle"])
        self.assertTrue(window["hiddenTitle"])
        self.assertFalse(window["transparent"])
        self.assertTrue(window["resizable"])
        self.assertEqual("http://127.0.0.1:5173", config["build"]["devUrl"])
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
        self.assertIn("action-grid", app)
        self.assertIn("tool-grid", app)
        self.assertIn("workbench-main", app)
        self.assertIn("workbench-preflight", app)
        self.assertIn("settings-shell", app)
        self.assertIn("settings-shell-meta", app)
        self.assertIn("page-stage--compact", app)
        self.assertIn("data-tauri-drag-region", app)
        self.assertIn("ConfirmDialog", app)
        self.assertIn("buildWorkflowConfirmCopy", app)
        self.assertIn("优选前确认", app)
        self.assertIn("summary-chips", app)
        self.assertIn("aria-label={`侧栏-${item.label}`}", app)
        self.assertIn('aria-current={activePage === item.id ? "page" : undefined}', app)
        self.assertIn("box-shadow", css)
        self.assertIn("linear-gradient", css)

    def test_react_styles_match_cockpit_navigation_details(self):
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        for token in ["--primary: #1d4ed8", "--bg-card:", "--shadow-lg:", "--edge-glow:"]:
            self.assertIn(token, css)

        self.assertIn(".page-tab::before", css)
        self.assertIn("--hover-lift-shadow:", css)
        self.assertIn("filter: blur(12px)", css)
        self.assertIn("transform: translateY(-1px) scale(1.04)", css)
        self.assertIn(".page-tab.active", css)
        self.assertIn("background: var(--primary)", css)
        self.assertIn("color: #fff", css)
        self.assertIn("filter: drop-shadow", css)

    def test_react_styles_keep_surfaces_rounded_and_text_safe(self):
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".sidebar-rail", css)
        self.assertIn("position: fixed", css)
        self.assertIn("top: 50%", css)
        self.assertIn("width: 68px", css)
        self.assertIn("border-radius: 30px", css)
        self.assertIn(".notice-pill span", css)
        self.assertNotIn("border-radius: 0;", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn(":focus-visible", css)
        self.assertIn(".drag-region", css)
        self.assertIn("-webkit-app-region: drag", css)
        self.assertIn("-webkit-app-region: no-drag", css)
        self.assertIn("scrollbar-gutter: stable", css)

    def test_react_styles_have_narrow_viewport_guardrails(self):
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 760px)", css)
        self.assertIn(".sidebar {\n    display: none;", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) !important", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("scrollbar-color", css)

    def test_react_styles_align_workbench_rows_and_soften_shadow_gutter(self):
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        self.assertIn('grid-template-areas:\n    "main status"\n    "tools preflight"\n    "latest log";', css)
        self.assertIn("--bar-shadow:", css)
        self.assertIn("box-shadow: var(--bar-shadow)", css)
        self.assertIn("row-gap: 18px", css)

    def test_react_styles_keep_cockpit_compact_density(self):
        app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("page-title-main", app)
        self.assertIn("task-title", app)
        self.assertIn("icon-badge", app)
        self.assertIn("isWorkbenchPage", app)
        self.assertIn("settings-fields--compact", app)
        self.assertIn("grid-template-columns: 120px minmax(0, 1fr)", css)
        self.assertIn("top: calc(50% - 251px)", css)
        self.assertIn("height: 48px", css)
        self.assertIn("font-size: 21px", css)
        self.assertIn("font-size: 18px", css)
        self.assertIn("border-radius: 24px", css)
        self.assertIn("min-height: 80px", css)
        self.assertIn("grid-template-columns: 38px minmax(0, 1fr)", css)
        self.assertIn("settings-shell-meta", css)
        self.assertIn("page-stage--compact", css)
        self.assertIn(".summary-chip", css)
        self.assertIn(".modal-backdrop", css)
        self.assertIn(".confirm-dialog", css)


if __name__ == "__main__":
    unittest.main()
