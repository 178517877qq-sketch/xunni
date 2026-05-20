import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.modules.setdefault("requests", Mock())
import main


class GitHubSyncProxyTests(unittest.TestCase):
    def test_build_github_sync_env_injects_proxy_only_for_sync(self):
        with patch.dict(os.environ, {"KEEP_ME": "1"}, clear=True):
            env = main.build_github_sync_env("http://127.0.0.1:7890")

        self.assertEqual(env["KEEP_ME"], "1")
        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:7890")
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:7890")
        self.assertEqual(env["ALL_PROXY"], "http://127.0.0.1:7890")
        self.assertNotIn("GITHUB_SYNC_PROXY_URL", env)

    def test_build_github_sync_env_leaves_proxy_unset_when_empty(self):
        with patch.dict(os.environ, {"KEEP_ME": "1"}, clear=True):
            env = main.build_github_sync_env("")

        self.assertEqual(env["KEEP_ME"], "1")
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("ALL_PROXY", env)


if __name__ == "__main__":
    unittest.main()
