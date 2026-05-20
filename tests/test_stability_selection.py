import unittest
import sys
from unittest.mock import Mock

sys.modules.setdefault("requests", Mock())
import main


class StabilitySelectionTests(unittest.TestCase):
    def test_stable_node_can_outrank_slightly_faster_new_node(self):
        stats = {
            "nodes": {
                "1.1.1.1:443#JP": {
                    "runs": 8,
                    "passes": 8,
                    "failures": 0,
                    "avg_speed_mbps": 72.0,
                    "best_speed_mbps": 90.0,
                    "avg_latency_ms": 45.0,
                    "best_latency_ms": 35.0,
                }
            }
        }
        bw_results = [
            ("1.1.1.1:443#JP", 70.0),
            ("2.2.2.2:443#JP", 86.0),
        ]
        latency_map = {
            "1.1.1.1:443#JP": 0.040,
            "2.2.2.2:443#JP": 0.042,
        }

        ranked = main.rank_bandwidth_results(bw_results, latency_map, stats)

        self.assertEqual("1.1.1.1:443#JP", ranked[0][0])

    def test_select_final_nodes_applies_per_country_limit_and_global_cap(self):
        ranked_results = [
            ("2.2.2.1:443#SG", 91.0),
            ("1.1.1.1:443#JP", 90.0),
            ("1.1.1.2:443#JP", 89.0),
            ("1.1.1.3:443#JP", 88.0),
            ("2.2.2.2:443#SG", 87.0),
            ("2.2.2.3:443#SG", 86.0),
            ("3.3.3.1:443#US", 85.0),
        ]

        selected = main.select_final_nodes(
            ranked_results=ranked_results,
            tcp_results=[],
            use_global_mode=False,
            global_top_n=24,
            per_country_top_n=2,
            output_node_limit=5,
        )

        self.assertEqual(
            [
                "2.2.2.1:443#SG",
                "1.1.1.1:443#JP",
                "1.1.1.2:443#JP",
                "2.2.2.2:443#SG",
                "3.3.3.1:443#US",
            ],
            selected,
        )

    def test_select_final_nodes_prefers_443_before_backup_ports_in_global_mode(self):
        ranked_results = [
            ("2.2.2.1:2053#SG", 99.0),
            ("1.1.1.1:443#JP", 90.0),
            ("3.3.3.1:8443#US", 89.0),
            ("4.4.4.4:443#HK", 88.0),
        ]

        selected = main.select_final_nodes(
            ranked_results=ranked_results,
            tcp_results=[],
            use_global_mode=True,
            global_top_n=3,
            per_country_top_n=2,
            output_node_limit=3,
        )

        self.assertEqual(
            [
                "1.1.1.1:443#JP",
                "4.4.4.4:443#HK",
                "2.2.2.1:2053#SG",
            ],
            selected,
        )

    def test_select_final_nodes_prefers_443_within_country_mode(self):
        ranked_results = [
            ("2.2.2.1:2053#SG", 99.0),
            ("1.1.1.1:443#JP", 90.0),
            ("3.3.3.1:8443#US", 89.0),
            ("4.4.4.4:443#SG", 88.0),
            ("5.5.5.5:443#US", 87.0),
        ]

        selected = main.select_final_nodes(
            ranked_results=ranked_results,
            tcp_results=[],
            use_global_mode=False,
            global_top_n=24,
            per_country_top_n=1,
            output_node_limit=3,
        )

        self.assertEqual(
            [
                "1.1.1.1:443#JP",
                "4.4.4.4:443#SG",
                "5.5.5.5:443#US",
            ],
            selected,
        )

    def test_select_final_nodes_prefers_443_when_falling_back_to_tcp_results(self):
        tcp_results = [
            ("2.2.2.1:2053#SG", 0.220, "SG", 3),
            ("1.1.1.1:443#JP", 0.300, "JP", 3),
            ("3.3.3.1:8443#US", 0.350, "US", 3),
        ]

        selected = main.select_final_nodes(
            ranked_results=[],
            tcp_results=tcp_results,
            use_global_mode=True,
            global_top_n=2,
            per_country_top_n=1,
            output_node_limit=2,
        )

        self.assertEqual(
            [
                "1.1.1.1:443#JP",
                "2.2.2.1:2053#SG",
            ],
            selected,
        )


if __name__ == "__main__":
    unittest.main()
