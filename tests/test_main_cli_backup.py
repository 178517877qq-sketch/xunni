import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.modules.setdefault("requests", Mock())
import main


class MainCliBackupTests(unittest.TestCase):
    def test_no_github_sync_flag_skips_sync_call(self):
        with patch.object(main, "sync_to_github") as sync:
            result = main.maybe_sync_to_github(no_github_sync=True)

        self.assertFalse(result)
        sync.assert_not_called()

    def test_sync_only_cli_calls_sync_without_running_optimizer(self):
        with patch.object(main, "sync_to_github") as sync, patch.object(main, "run_optimization") as optimize:
            main.run_cli(["--sync-only"])

        sync.assert_called_once_with()
        optimize.assert_not_called()

    def test_no_github_sync_cli_passes_skip_flag_to_optimizer(self):
        with patch.object(main, "run_optimization") as optimize:
            main.run_cli(["--no-github-sync"])

        optimize.assert_called_once_with(no_github_sync=True)

    def test_backup_output_file_keeps_only_requested_number_of_backups(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output = root / "ip.txt"
            backup_dir = root / "backups"
            backup_dir.mkdir()
            output.write_text("1.1.1.1:443#US\n", encoding="utf-8")

            for index in range(3):
                old_backup = backup_dir / f"ip.txt.20260101-00000{index}.bak"
                old_backup.write_text(f"old-{index}\n", encoding="utf-8")
                os.utime(old_backup, (index + 1, index + 1))

            backup_path = main.backup_output_file(
                output_file=str(output),
                backup_dir=str(backup_dir),
                keep=2,
                enabled=True,
            )

            backups = sorted(backup_dir.glob("ip.txt.*.bak"))

        self.assertIsNotNone(backup_path)
        self.assertEqual(2, len(backups))
        self.assertTrue(Path(backup_path).name in {path.name for path in backups})
        self.assertNotIn("ip.txt.20260101-000000.bak", {path.name for path in backups})


if __name__ == "__main__":
    unittest.main()
