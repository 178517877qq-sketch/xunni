import unittest

import ui_bridge


class UiBridgeTests(unittest.TestCase):
    def test_build_state_returns_dashboard_snapshot_shape(self):
        state = ui_bridge.build_state()

        self.assertIn("config_path", state)
        self.assertIn("python_exe", state)
        self.assertIn("output_preview", state)
        self.assertIsInstance(state["output_preview"], list)
        self.assertGreaterEqual(state["output_count"], 0)
        self.assertGreaterEqual(len(state["cards"]), 3)
        self.assertIn("preflight", state)
        self.assertIn("text", state["preflight"])

    def test_proxy_check_without_proxy_reports_missing_configuration(self):
        result = ui_bridge.test_proxy("")

        self.assertFalse(result["ok"])
        self.assertEqual("", result["proxy_url"])
        self.assertIn("GITHUB_SYNC_PROXY_URL", result["message"])


if __name__ == "__main__":
    unittest.main()
