import tempfile
import unittest
from pathlib import Path

from belentani_ops import llm, monitor, report, secrets, system, util
from belentani_ops.config import Config, load_config, save_config


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertGreaterEqual(cfg.disk_warn_gb, cfg.disk_block_gb)
        self.assertTrue(cfg.sites)
        self.assertTrue(cfg.providers)

    def test_roundtrip(self):
        cfg = Config()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            save_config(cfg, path)
            loaded, source = load_config(path)
            self.assertEqual(loaded.github_user, cfg.github_user)
            self.assertEqual(source, path)


class TestUtil(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(util.mask(""), "")
        self.assertEqual(util.mask("abcd", keep=2), "****")
        masked = util.mask("sk-sp-abcdefghijklmnop", keep=4)
        self.assertTrue(masked.startswith("sk-s"))
        self.assertIn("*", masked)

    def test_human_bytes(self):
        self.assertEqual(util.human_bytes(0), "0.0B")
        self.assertIn("KB", util.human_bytes(2048))

    def test_redact_text(self):
        text = "key sk-sp-abcdefghijklmnopqrst done"
        out = util.redact_text(text)
        self.assertNotIn("abcdefghijklmnopqrst", out)


class TestSecrets(unittest.TestCase):
    def test_scan_file_detects(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "creds.txt"
            f.write_text("HF=hf_abcdefghijklmnopqrstuvwx\nsafe=hello\n", encoding="utf-8")
            hits = secrets.scan_file(f)
            self.assertTrue(any(h["kind"] == "huggingface" for h in hits))

    def test_scan_file_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "clean.py"
            f.write_text("print('hello world')\n", encoding="utf-8")
            self.assertEqual(secrets.scan_file(f), [])


class TestLlm(unittest.TestCase):
    def test_route_and_pick(self):
        cfg = Config()
        chain = llm.route("coding", cfg)
        self.assertTrue(chain)
        choice = llm.pick("coding", cfg)
        self.assertIn(choice, cfg.providers)

    def test_provider_status(self):
        cfg = Config()
        rows = llm.provider_status(cfg)
        self.assertEqual(len(rows), len(cfg.providers))


class TestSystem(unittest.TestCase):
    def test_disk_report(self):
        cfg = Config()
        rows = system.disk_report(cfg)
        self.assertTrue(rows)

    def test_home_root_guard(self):
        findings = system.home_root_guard()
        self.assertIn("stray_files", findings)
        self.assertIn("junk_dirs", findings)


class TestMonitor(unittest.TestCase):
    def test_check_url_bad_host(self):
        result = monitor.check_url("http://127.0.0.1:1/does-not-exist", timeout=2)
        self.assertFalse(result["ok"])


class TestReport(unittest.TestCase):
    def test_full_report_offline(self):
        cfg = Config()
        cfg.sites = []
        data = report.full_report(cfg, deep=False, include_scan=False, include_monitor=False)
        self.assertIn("disk", data)
        self.assertIn("llm", data)
        self.assertIsInstance(data["llm"]["costs"]["total_usd"], float)


class TestCli(unittest.TestCase):
    def test_parser_builds(self):
        from belentani_ops.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["llm", "route", "--task", "coding"])
        self.assertEqual(args.command, "llm")
        self.assertEqual(args.task, "coding")

    def test_main_doctor(self):
        from belentani_ops.cli import main
        code = main(["doctor"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
