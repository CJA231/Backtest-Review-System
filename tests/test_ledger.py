"""Accounting acceptance tests using independent, reconciled CSV fixtures."""

from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from trading_journal.ledger import DataError, build_report


ROOT = Path(__file__).resolve().parents[1]


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data = Path(self.temporary.name) / "records"
        shutil.copytree(ROOT / "examples" / "2026", self.data)
        (self.data / "dataset.json").write_text(
            json.dumps({
                "schema_version": 2,
                "account_id": "DEMO-01",
                "currency": "MYR",
                "timezone_offset": "+08:00",
                "fictional": True,
                "cost_method": "FIFO",
            }),
            encoding="utf-8",
        )
        # Most tests deliberately have no reported return series.
        (self.data / "broker-performance.csv").unlink(missing_ok=True)

    def rows(self, name: str) -> list[dict[str, str]]:
        with (self.data / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def write_rows(self, name: str, rows: list[dict], fields=None) -> None:
        if fields is None:
            with (self.data / name).open(encoding="utf-8", newline="") as stream:
                fields = next(csv.reader(stream))
        with (self.data / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def contribution(self, report: dict, strategy: str) -> float:
        matches = [row for row in report["contributions"]
                   if strategy in str(row["label"]).upper()]
        self.assertEqual(len(matches), 1, f"Expected one contribution for {strategy}")
        return float(matches[0]["value"])

    def assert_rejected(self) -> None:
        with self.assertRaises(DataError):
            build_report(self.data)

    def performance_rows(self, *, currency="MYR", coverage="complete") -> None:
        fields = ["date", "account_id", "return_index", "benchmark_index",
                  "currency", "basis", "coverage", "source"]
        dates = [row["date"] for row in self.rows("daily-assets.csv")]
        rows = [{"date": day, "account_id": "DEMO-01",
                 "return_index": "101" if i == len(dates) - 1 else "100",
                 "benchmark_index": "100", "currency": currency,
                 "basis": "TWR_INDEX", "source": "Fictional broker TWR",
                 "coverage": "baseline" if i == 0 else
                             coverage if i == len(dates) - 1 else "complete"}
                for i, day in enumerate(dates)]
        self.write_rows("broker-performance.csv", rows, fields)

    def test_fictional_account_reconciles(self) -> None:
        report = build_report(self.data)
        summary = report["summary"]
        self.assertAlmostEqual(float(summary["closing_nav"]), 110111)
        self.assertAlmostEqual(float(summary["net_pnl"]), 111)
        self.assertAlmostEqual(float(summary["fees"]), 9)
        self.assertEqual(summary["total_fills"], 7)
        self.assertEqual(summary["total_orders"], 6)
        self.assertEqual(summary["new_trades"], 3)
        self.assertEqual(summary["closed_trades"], 2)
        self.assertAlmostEqual(self.contribution(report, "TREND"), 295)
        self.assertAlmostEqual(self.contribution(report, "BREAKOUT"), -204)

    def test_partial_exit_preserves_fifo_cost_and_open_pnl(self) -> None:
        cutoff = "2026-01-06"
        for name in ("daily-assets.csv", "positions-daily.csv"):
            self.write_rows(name, [r for r in self.rows(name) if r["date"] <= cutoff])
        self.write_rows("fills.csv", [r for r in self.rows("fills.csv")
                                      if r["timestamp"][:10] <= cutoff])
        self.write_rows("cash-events.csv", [])
        trades = [r for r in self.rows("trades.csv") if r["trade_id"] == "TR-001"]
        trades[0]["status"] = "OPEN"
        trades[0]["closed_at"] = ""
        self.write_rows("trades.csv", trades)
        self.write_rows("behavior-events.csv", [r for r in self.rows("behavior-events.csv")
                                               if r["trade_id"] == "TR-001"])

        report = build_report(self.data)
        # Sold first lot: 1099 - 1001 = 98. Remaining lot: 1100 - 1021 = 79.
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), 177)
        self.assertAlmostEqual(float(report["summary"]["closing_nav"]), 100177)
        self.assertAlmostEqual(self.contribution(report, "TREND"), 177)
        self.assertEqual(report["summary"]["closed_trades"], 0)
        self.assertEqual(report["summary"]["total_fills"], 3)
        self.assertEqual(report["summary"]["total_orders"], 2)

    def test_missing_returns_never_invents_twr_from_nav(self) -> None:
        report = build_report(self.data)
        self.assertIsNone(report["returns"])
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), 111)

    def test_return_gap_suppresses_whole_period_metrics(self) -> None:
        self.performance_rows(coverage="gap")
        self.assertIsNone(build_report(self.data)["returns"])

    def test_missing_internal_index_date_suppresses_performance(self) -> None:
        self.performance_rows()
        rows = self.rows("broker-performance.csv")
        self.write_rows("broker-performance.csv", [r for r in rows if r["date"] != "2026-01-06"])
        report = build_report(self.data)
        self.assertIsNone(report["returns"])
        self.assertTrue(any("日期" in warning for warning in report["warnings"]))

    def test_additional_internal_index_dates_are_allowed(self) -> None:
        self.performance_rows()
        rows = self.rows("broker-performance.csv")
        extra = dict(rows[1], date="2026-01-03")
        self.write_rows("broker-performance.csv", rows + [extra])
        result = build_report(self.data)["returns"]
        self.assertAlmostEqual(float(result["total_return_pct"]), 1)
        self.assertEqual(len(result["rows"]), len(rows) + 1)

    def test_complete_reported_index_has_one_percent_return_and_zero_drawdown(self) -> None:
        self.performance_rows()
        result = build_report(self.data)["returns"]
        self.assertIsNotNone(result)
        self.assertAlmostEqual(float(result["total_return_pct"]), 1)
        self.assertAlmostEqual(float(result["max_drawdown_pct"]), 0)

    def test_incomplete_benchmark_is_omitted_without_losing_account_return(self) -> None:
        self.performance_rows()
        rows = self.rows("broker-performance.csv")
        rows[0]["benchmark_index"] = ""
        self.write_rows("broker-performance.csv", rows)
        result = build_report(self.data)["returns"]
        self.assertAlmostEqual(float(result["total_return_pct"]), 1)
        self.assertTrue(all(row["benchmark_index"] is None for row in result["rows"]))

    def test_cash_deposit_changes_nav_but_not_reported_index_return(self) -> None:
        for name in ("fills.csv", "trades.csv", "positions-daily.csv", "behavior-events.csv"):
            self.write_rows(name, [])
        self.write_rows("cash-events.csv", [r for r in self.rows("cash-events.csv")
                                           if r["event_type"] == "DEPOSIT"])
        snapshots = self.rows("daily-assets.csv")
        for row in snapshots:
            row.update(cash="110000" if row["date"] == "2026-01-12" else "100000",
                       positions_market_value="0", realized_pnl_ytd="0",
                       unrealized_pnl="0", fees_ytd="0")
            row["nav"] = row["cash"]
        self.write_rows("daily-assets.csv", snapshots)
        self.performance_rows()
        indices = self.rows("broker-performance.csv")
        indices[-1]["return_index"] = "100"
        self.write_rows("broker-performance.csv", indices)

        report = build_report(self.data)
        self.assertAlmostEqual(float(report["summary"]["closing_nav"]), 110000)
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), 0)
        self.assertEqual(report["summary"]["total_fills"], 0)
        self.assertAlmostEqual(float(report["returns"]["total_return_pct"]), 0)
        self.assertAlmostEqual(float(report["returns"]["max_drawdown_pct"]), 0)

    def test_raw_nav_cannot_be_labeled_as_twr_index(self) -> None:
        self.performance_rows()
        rows = self.rows("broker-performance.csv")
        rows[-1]["basis"] = "NAV"
        self.write_rows("broker-performance.csv", rows)
        self.assert_rejected()

    def test_foreign_return_currency_is_rejected(self) -> None:
        self.performance_rows(currency="USD")
        self.assert_rejected()

    def test_duplicate_fill_is_rejected(self) -> None:
        rows = self.rows("fills.csv")
        self.write_rows("fills.csv", rows + [dict(rows[0])])
        self.assert_rejected()

    def test_duplicate_broker_fill_with_new_local_id_is_rejected(self) -> None:
        rows = self.rows("fills.csv")
        rows[1]["broker_fill_id"] = rows[0]["broker_fill_id"]
        self.write_rows("fills.csv", rows)
        self.assert_rejected()

    def test_overselling_a_trade_is_rejected(self) -> None:
        rows = self.rows("fills.csv")
        rows[5]["quantity"] = "201"
        self.write_rows("fills.csv", rows)
        self.assert_rejected()

    def reopened_trade_fixture(self, *, same_timestamp=False) -> None:
        """Relabel a later new holding as a prior, fully exited trade."""
        fills = self.rows("fills.csv")
        fills[-1]["trade_id"] = "TR-001"
        if same_timestamp:
            fills[-1]["timestamp"] = fills[3]["timestamp"]
        self.write_rows("fills.csv", fills)
        trades = [r for r in self.rows("trades.csv") if r["trade_id"] != "TR-003"]
        trades[0]["status"] = "OPEN"
        trades[0]["closed_at"] = ""
        self.write_rows("trades.csv", trades)
        positions = self.rows("positions-daily.csv")
        positions[-1]["trade_id"] = "TR-001"
        positions[-1]["symbol"] = "DEMO_A"
        if same_timestamp:
            for day in ("2026-01-07", "2026-01-08", "2026-01-09"):
                positions.append({"date": day, "account_id": "DEMO-01", "trade_id": "TR-001",
                                  "symbol": "DEMO_A", "quantity": 100, "mark_price": 30,
                                  "cost_basis": 3001, "market_value": 3000,
                                  "unrealized_pnl": -1, "source": "Fictional reopening"})
            snapshots = self.rows("daily-assets.csv")
            for row in snapshots:
                if row["date"] in {"2026-01-07", "2026-01-08", "2026-01-09"}:
                    row["cash"] = str(int(row["cash"]) - 3001)
                    row["positions_market_value"] = str(int(row["positions_market_value"]) + 3000)
                    row["nav"] = str(int(row["nav"]) - 1)
                    row["unrealized_pnl"] = str(int(row["unrealized_pnl"]) - 1)
                    row["fees_ytd"] = str(int(row["fees_ytd"]) + 1)
            self.write_rows("daily-assets.csv", snapshots)
        self.write_rows("positions-daily.csv", positions)

    def test_fully_exited_trade_requires_new_trade_id_for_later_buy(self) -> None:
        self.reopened_trade_fixture()
        with self.assertRaisesRegex(DataError, "trade_id"):
            build_report(self.data)

    def test_full_exit_and_reentry_same_timestamp_still_requires_new_id(self) -> None:
        self.reopened_trade_fixture(same_timestamp=True)
        with self.assertRaisesRegex(DataError, "trade_id"):
            build_report(self.data)

    def test_negative_transaction_fee_is_rejected(self) -> None:
        rows = self.rows("fills.csv")
        rows[0]["fees"] = "-1"
        self.write_rows("fills.csv", rows)
        self.assert_rejected()

    def test_wrong_nav_is_rejected(self) -> None:
        rows = self.rows("daily-assets.csv")
        rows[-1]["nav"] = "110112"
        self.write_rows("daily-assets.csv", rows)
        self.assert_rejected()

    def test_duplicate_daily_snapshot_is_rejected(self) -> None:
        rows = self.rows("daily-assets.csv")
        self.write_rows("daily-assets.csv", rows + [dict(rows[-1])])
        self.assert_rejected()

    def test_foreign_cash_event_account_is_rejected(self) -> None:
        rows = self.rows("cash-events.csv")
        rows[0]["account_id"] = "OTHER-ACCOUNT"
        self.write_rows("cash-events.csv", rows)
        self.assert_rejected()

    def test_missing_required_dataset_metadata_is_rejected(self) -> None:
        (self.data / "dataset.json").unlink()
        self.assert_rejected()

    def test_fictional_metadata_must_be_a_boolean(self) -> None:
        path = self.data / "dataset.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["fictional"] = "true"
        path.write_text(json.dumps(metadata), encoding="utf-8")
        self.assert_rejected()

    def test_fill_on_baseline_date_is_rejected(self) -> None:
        rows = self.rows("fills.csv")
        rows[0]["timestamp"] = "2025-12-31T10:00:00+08:00"
        self.write_rows("fills.csv", rows)
        self.assert_rejected()

    def test_cash_event_on_baseline_date_is_rejected(self) -> None:
        rows = self.rows("cash-events.csv")
        rows[0]["timestamp"] = "2025-12-31T08:00:00+08:00"
        self.write_rows("cash-events.csv", rows)
        self.assert_rejected()

    def cross_year_fixture(self, *, opening_position=False, opening_lots=False) -> None:
        """Prior-year gain 20, carried position, current-year sale gain 98."""
        with (self.data / "daily-assets.csv").open(encoding="utf-8", newline="") as stream:
            snapshot_fields = next(csv.reader(stream))
        values = [
            ("2025-12-29", 10000, 0, 10000, 0, 0, 0),
            ("2025-12-30", 9019, 1000, 10019, 20, -1, 1),
            ("2025-12-31", 9019, 1200, 10219, 20, 199, 1),
            ("2026-01-02", 10118, 0, 10118, 98, 0, 1),
        ]
        snapshots = [{"date": d, "account_id": "DEMO-01", "cash": cash,
                      "positions_market_value": mv, "nav": nav, "external_flow": 0,
                      "realized_pnl_ytd": realized, "unrealized_pnl": unrealized,
                      "fees_ytd": fees, "source": "Independent fictional fixture"}
                     for d, cash, mv, nav, realized, unrealized, fees in values]
        if opening_position:
            snapshots = snapshots[2:]
        self.write_rows("daily-assets.csv", snapshots, snapshot_fields)

        trades = [
            {"trade_id": "TR-OLD", "account_id": "DEMO-01", "symbol": "DEMO_OLD",
             "strategy_id": "TREND", "strategy_version": "v1",
             "opened_at": "2025-12-30T09:00:00+08:00",
             "closed_at": "2025-12-30T09:05:00+08:00", "planned_entry": 10,
             "planned_stop": 9, "initial_risk": 20, "status": "CLOSED",
             "plan_path": "examples/2026/review.md"},
            {"trade_id": "TR-CARRY", "account_id": "DEMO-01", "symbol": "DEMO_CARRY",
             "strategy_id": "TREND", "strategy_version": "v1",
             "opened_at": "2025-12-30T10:00:00+08:00",
             "closed_at": "2026-01-02T10:00:00+08:00", "planned_entry": 10,
             "planned_stop": 9, "initial_risk": 150, "status": "CLOSED",
             "plan_path": "examples/2026/review.md"},
        ]
        self.write_rows("trades.csv", trades[1:] if opening_position else trades)
        fills = [
            {"fill_id": "X-1", "broker_fill_id": "BX-1", "broker_order_id": "OX-1",
             "trade_id": "TR-OLD", "timestamp": "2025-12-30T09:00:00+08:00",
             "side": "BUY", "quantity": 10, "price": 10, "fees": 0},
            {"fill_id": "X-2", "broker_fill_id": "BX-2", "broker_order_id": "OX-2",
             "trade_id": "TR-OLD", "timestamp": "2025-12-30T09:05:00+08:00",
             "side": "SELL", "quantity": 10, "price": 12, "fees": 0},
            {"fill_id": "X-3", "broker_fill_id": "BX-3", "broker_order_id": "OX-3",
             "trade_id": "TR-CARRY", "timestamp": "2025-12-30T10:00:00+08:00",
             "side": "BUY", "quantity": 100, "price": 10, "fees": 1},
            {"fill_id": "X-4", "broker_fill_id": "BX-4", "broker_order_id": "OX-4",
             "trade_id": "TR-CARRY", "timestamp": "2026-01-02T10:00:00+08:00",
             "side": "SELL", "quantity": 100, "price": 11, "fees": 1},
        ]
        self.write_rows("fills.csv", fills[3:] if opening_position else fills)
        positions = [
            {"date": d, "account_id": "DEMO-01", "trade_id": "TR-CARRY",
             "symbol": "DEMO_CARRY", "quantity": 100, "mark_price": mark,
             "cost_basis": 1001, "market_value": market, "unrealized_pnl": pnl,
             "source": "Independent fictional fixture"}
            for d, mark, market, pnl in [
                ("2025-12-30", 10, 1000, -1), ("2025-12-31", 12, 1200, 199)
            ]
        ]
        self.write_rows("positions-daily.csv", positions[1:] if opening_position else positions)
        self.write_rows("cash-events.csv", [])
        self.write_rows("behavior-events.csv", [])
        strategies = [r for r in self.rows("strategies.csv") if r["strategy_id"] == "TREND"]
        strategies[0]["active_from"] = "2025-12-01"
        self.write_rows("strategies.csv", strategies)
        if opening_lots:
            self.write_rows("opening-lots.csv", [
                {"lot_id": "L-1", "trade_id": "TR-CARRY",
                 "acquired_at": "2025-12-30T10:00:00+08:00",
                 "quantity": 100, "cost_basis": 1001},
            ], ["lot_id", "trade_id", "acquired_at", "quantity", "cost_basis"])

    def test_cross_year_ytd_resets_without_resetting_fifo_cost(self) -> None:
        self.cross_year_fixture()
        report = build_report(self.data)
        # Whole observation period: prior-year 20 + current-year 98 = 118.
        # January snapshot requires realized YTD 98, not 118, and fees YTD 1, not 2.
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), 118)
        self.assertAlmostEqual(float(report["summary"]["closing_nav"]), 10118)
        self.assertAlmostEqual(self.contribution(report, "TREND"), 118)
        self.assertEqual(report["summary"]["closed_trades"], 2)

    def test_nonflat_baseline_requires_opening_lots(self) -> None:
        self.cross_year_fixture(opening_position=True)
        self.assert_rejected()

    def test_opening_lots_use_change_in_unrealized_pnl(self) -> None:
        self.cross_year_fixture(opening_position=True, opening_lots=True)
        report = build_report(self.data)
        # January's monetary contribution: realized 98 minus opening unrealized 199.
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), -101)
        self.assertAlmostEqual(self.contribution(report, "TREND"), -101)
        self.assertAlmostEqual(float(report["summary"]["fees"]), 1)
        self.assertEqual(report["summary"]["new_trades"], 0)
        self.assertEqual(report["summary"]["closed_trades"], 1)

    def test_opening_lot_cost_must_match_baseline_position(self) -> None:
        self.cross_year_fixture(opening_position=True, opening_lots=True)
        rows = self.rows("opening-lots.csv")
        rows[0]["cost_basis"] = "1002"
        self.write_rows("opening-lots.csv", rows)
        self.assert_rejected()

    def backtest_fixture(self) -> Path:
        folder = self.data / "backtest"
        folder.mkdir()
        metadata = {
            "schema_version": 2, "run_id": "TEST-RUN", "label": "Fictional test run",
            "currency": "MYR", "strategy_id": "TREND", "strategy_version": "v1",
            "source": "Independent fictional fixture",
            "costs": {"commission": "Included in supplied index", "slippage": "Included"},
            "notes": "No real trading advantage is claimed.", "initial_capital": 10000,
            "flow_policy": "NONE", "continuous_index": True,
        }
        (folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        self.write_rows("backtest/equity.csv", [
            {"run_id": "TEST-RUN", "date": "2024-01-02", "return_index": 100,
             "benchmark_index": 100, "phase": "IS"},
            {"run_id": "TEST-RUN", "date": "2024-01-03", "return_index": 90,
             "benchmark_index": 100, "phase": "IS"},
            {"run_id": "TEST-RUN", "date": "2024-01-04", "return_index": 110,
             "benchmark_index": 100, "phase": "OOS"},
        ], ["run_id", "date", "return_index", "benchmark_index", "phase"])
        return folder

    def test_continuous_backtest_index_is_separate_from_account_results(self) -> None:
        report = build_report(self.data, self.backtest_fixture())
        self.assertAlmostEqual(float(report["summary"]["net_pnl"]), 111)
        self.assertIsNone(report["returns"])
        self.assertAlmostEqual(float(report["backtest"]["total_return_pct"]), 10)
        self.assertAlmostEqual(float(report["backtest"]["max_drawdown_pct"]), -10)
        self.assertEqual([r["phase"] for r in report["backtest"]["rows"]], ["IS", "IS", "OOS"])

    def test_backtest_cannot_mix_run_ids(self) -> None:
        folder = self.backtest_fixture()
        rows = self.rows("backtest/equity.csv")
        rows[-1]["run_id"] = "ANOTHER-RUN"
        self.write_rows("backtest/equity.csv", rows)
        with self.assertRaises(DataError):
            build_report(self.data, folder)

    def test_backtest_requires_declared_continuous_index(self) -> None:
        folder = self.backtest_fixture()
        path = folder / "metadata.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["continuous_index"] = False
        path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaises(DataError):
            build_report(self.data, folder)

    def test_backtest_cannot_return_to_in_sample_after_out_of_sample(self) -> None:
        folder = self.backtest_fixture()
        rows = self.rows("backtest/equity.csv")
        rows[1]["phase"] = "OOS"
        rows[2]["phase"] = "IS"
        self.write_rows("backtest/equity.csv", rows)
        with self.assertRaises(DataError):
            build_report(self.data, folder)


if __name__ == "__main__":
    unittest.main()
