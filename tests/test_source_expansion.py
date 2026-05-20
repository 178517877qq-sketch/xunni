import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.modules.setdefault("requests", Mock())
import main


class SourceExpansionTests(unittest.TestCase):
    def test_sample_cloudflare_ipv4_cidr_generates_limited_443_candidates(self):
        nodes = main.sample_cloudflare_ipv4_cidrs(
            cidrs=["198.51.100.0/24"],
            ports=[443],
            sample_per_24=3,
            country_code="CF",
        )

        self.assertEqual(
            [
                "198.51.100.1:443#CF",
                "198.51.100.128:443#CF",
                "198.51.100.254:443#CF",
            ],
            nodes,
        )

    def test_load_local_seed_files_parses_existing_node_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            seed = Path(tmpdir) / "seed.txt"
            seed.write_text("1.1.1.1:443#JP\n2.2.2.2:2053#SG\n", encoding="utf-8")

            nodes = main.load_local_seed_files([str(seed)])

        self.assertEqual(["1.1.1.1:443#JP", "2.2.2.2:2053#SG"], nodes)

    def test_merge_nodes_dedupes_by_ip_port_not_ip_only(self):
        merged = main.merge_nodes_preserve_order(
            [
                ["1.1.1.1:443#JP", "1.1.1.1:2053#JP"],
                ["1.1.1.1:443#JP", "2.2.2.2:443#SG"],
            ]
        )

        self.assertEqual(
            ["1.1.1.1:443#JP", "1.1.1.1:2053#JP", "2.2.2.2:443#SG"],
            merged,
        )

    def test_fetch_cloudflare_official_ipv4_source_uses_official_endpoint_text(self):
        response = Mock()
        response.text = "198.51.100.0/24\n203.0.113.0/24\n"
        response.raise_for_status = Mock()

        with patch.object(main.requests, "get", return_value=response):
            nodes = main.fetch_cloudflare_official_ipv4_source(
                url="https://www.cloudflare.com/ips-v4",
                ports=[443],
                sample_per_24=1,
                country_code="CF",
            )

        self.assertEqual(["198.51.100.1:443#CF", "203.0.113.1:443#CF"], nodes)

    def test_country_prefilter_allows_official_sampling_placeholder_country(self):
        self.assertTrue(
            main.is_country_allowed_for_pre_filter(
                "198.51.100.1:443#CF",
                allowed_countries={"US", "JP"},
                official_country_code="CF",
                official_sampling_enabled=True,
            )
        )

    def test_relabel_nodes_with_exit_country_uses_availability_country(self):
        nodes, ip_info, exit_details, aliases = main.relabel_nodes_with_exit_country(
            nodes=["198.51.100.1:443#CF", "2.2.2.2:443#SG"],
            ip_info={"198.51.100.1:443#CF": "dual_stack", "2.2.2.2:443#SG": "ipv4_only"},
            exit_details={"198.51.100.1:443#CF": {"country": "JP"}, "2.2.2.2:443#SG": {}},
        )

        self.assertEqual(["198.51.100.1:443#JP", "2.2.2.2:443#SG"], nodes)
        self.assertEqual({"198.51.100.1:443#JP": "dual_stack", "2.2.2.2:443#SG": "ipv4_only"}, ip_info)
        self.assertEqual({"198.51.100.1:443#JP": {"country": "JP"}, "2.2.2.2:443#SG": {}}, exit_details)
        self.assertEqual({"198.51.100.1:443#CF": "198.51.100.1:443#JP"}, aliases)


if __name__ == "__main__":
    unittest.main()
