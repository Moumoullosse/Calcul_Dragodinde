import unittest
from collections import defaultdict

from core.data import RATIO_BY_NAME, SESSION_PAIR_CAPACITY
from core.planner import default_stock, plan_session


class PlanSessionGenerationBalancingTests(unittest.TestCase):
    def _created_pairs(self, results: dict[str, object]) -> dict[str, int]:
        created_pairs: dict[str, int] = defaultdict(int)
        for row in results["recap_creation_rows"]:
            created_pairs[row["Dragodinde creee"]] += row["Paires creees"]
        return dict(created_pairs)

    def test_same_generation_breeds_keep_natural_balance_when_both_are_feasible(self) -> None:
        stock = default_stock()

        for breed_name in ("Amande-Dore", "Amande-Rousse", "Dore-Rousse"):
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = self._created_pairs(results)

        capacity_pairs = 250 // 2
        expected_ebene_pairs = round(RATIO_BY_NAME["Ebene"] * capacity_pairs)
        expected_indigo_pairs = round(RATIO_BY_NAME["Indigo"] * capacity_pairs)

        self.assertGreaterEqual(created_pairs.get("Ebene", 0), expected_ebene_pairs)
        self.assertGreaterEqual(created_pairs.get("Indigo", 0), expected_indigo_pairs)
        self.assertGreater(created_pairs.get("Ebene", 0), 0)

    def test_generation_budget_spills_to_other_feasible_breeds_when_one_is_blocked(self) -> None:
        stock = default_stock()

        stock["Amande-Rousse"].males = 50
        stock["Amande-Rousse"].females = 50
        stock["Ebene-Indigo"].males = 50
        stock["Ebene-Indigo"].females = 50

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = self._created_pairs(results)

        self.assertEqual(created_pairs.get("Pourpre", 0), 100)
        self.assertEqual(created_pairs.get("Orchidee", 0), 0)

    def test_generation_surplus_is_maximized_before_lower_generations(self) -> None:
        stock = default_stock()

        stock["Ebene"].males = 22
        stock["Ebene"].females = 15
        stock["Indigo"].males = 25
        stock["Indigo"].females = 10

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = self._created_pairs(results)

        self.assertEqual(created_pairs.get("Ebene-Indigo", 0), 25)

    def test_stock_balancing_reduces_creation_for_already_stocked_breed(self) -> None:
        stock = default_stock()

        for breed_name in ("Amande-Dore", "Amande-Rousse", "Dore-Rousse", "Ebene-Indigo"):
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        pourpre_target_stock = round(RATIO_BY_NAME["Pourpre"] * SESSION_PAIR_CAPACITY)
        stock["Pourpre"].males = pourpre_target_stock
        stock["Pourpre"].females = pourpre_target_stock

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
            balance_by_existing_stock=True,
        )

        created_pairs = self._created_pairs(results)
        final_rows = {
            row["Dragodinde"]: row
            for row in results["final_rows"]
        }

        self.assertEqual(created_pairs.get("Pourpre", 0), 0)
        self.assertEqual(final_rows["Pourpre"]["Paires cibles"], 0)
        self.assertEqual(created_pairs.get("Orchidee", 0), 125)

    def test_stock_balancing_keeps_generation_total(self) -> None:
        stock = default_stock()

        for breed_name in ("Amande-Dore", "Amande-Rousse", "Dore-Rousse", "Ebene-Indigo"):
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        # G5 already has Pourpre in stock, so the generation budget should shift to Orchidee,
        # not disappear from generation 5.
        stock["Pourpre"].males = round(RATIO_BY_NAME["Pourpre"] * SESSION_PAIR_CAPACITY)
        stock["Pourpre"].females = round(RATIO_BY_NAME["Pourpre"] * SESSION_PAIR_CAPACITY)

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
            balance_by_existing_stock=True,
        )

        final_rows = results["final_rows"]
        generation_five_rows = [row for row in final_rows if row["Gen"] == 5]

        planned_generation_total = sum(row["Paires cibles"] for row in generation_five_rows)
        base_generation_total = sum(row["Paires cibles ratio session"] for row in generation_five_rows)

        self.assertEqual(planned_generation_total, base_generation_total)
        self.assertEqual(next(row for row in generation_five_rows if row["Dragodinde"] == "Pourpre")["Paires cibles"], 0)
        self.assertEqual(next(row for row in generation_five_rows if row["Dragodinde"] == "Orchidee")["Paires cibles"], base_generation_total)

    def test_stock_balancing_still_maximizes_same_generation_surplus(self) -> None:
        stock = default_stock()

        stock["Ebene"].males = 22
        stock["Ebene"].females = 15
        stock["Indigo"].males = 25
        stock["Indigo"].females = 10
        stock["Ebene-Indigo"].males = 13
        stock["Ebene-Indigo"].females = 6

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
            balance_by_existing_stock=True,
        )

        created_pairs = self._created_pairs(results)

        self.assertEqual(created_pairs.get("Ebene-Indigo", 0), 25)

    def test_stock_balancing_does_not_increase_g1_fill_against_baseline(self) -> None:
        stock = default_stock()

        for breed_name in stock:
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        stock["Pourpre"].males = round(RATIO_BY_NAME["Pourpre"] * SESSION_PAIR_CAPACITY)
        stock["Pourpre"].females = round(RATIO_BY_NAME["Pourpre"] * SESSION_PAIR_CAPACITY)

        baseline_results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=True,
            balance_by_existing_stock=False,
        )

        balanced_results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=True,
            balance_by_existing_stock=True,
        )

        self.assertEqual(
            balanced_results["controls"]["Paires G1 ajoutees"],
            baseline_results["controls"]["Paires G1 ajoutees"],
        )

    def test_real_created_pairs_stay_zero_when_required_parents_are_missing(self) -> None:
        stock = default_stock()

        stock["Amande-Rousse"].males = 18
        stock["Amande-Rousse"].females = 16
        stock["Amande-Dore"].males = 13
        stock["Amande-Dore"].females = 14
        stock["Dore-Rousse"].males = 9
        stock["Dore-Rousse"].females = 12
        stock["Ebene"].males = 22
        stock["Ebene"].females = 15
        stock["Indigo"].males = 25
        stock["Indigo"].females = 10
        stock["Ebene-Indigo"].males = 13
        stock["Ebene-Indigo"].females = 6
        stock["Pourpre"].males = 7
        stock["Pourpre"].females = 7
        stock["Orchidee"].males = 3
        stock["Orchidee"].females = 4
        stock["Ebene-Orchidee"].males = 0
        stock["Ebene-Orchidee"].females = 2
        stock["Orchidee-Pourpre"].males = 1
        stock["Orchidee-Pourpre"].females = 1
        stock["Indigo-Pourpre"].males = 2
        stock["Indigo-Pourpre"].females = 2

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=True,
            balance_by_existing_stock=True,
        )

        final_rows = {
            row["Dragodinde"]: row
            for row in results["final_rows"]
        }

        self.assertEqual(final_rows["Ivoire-Turquoise"]["Paires reellement creees"], 0)
        self.assertFalse(final_rows["Ivoire-Turquoise"]["Creation realisable"])
        self.assertGreaterEqual(final_rows["Turquoise"]["Paires reellement creees"], 1)
        self.assertGreaterEqual(final_rows["Ivoire"]["Paires reellement creees"], 1)


if __name__ == "__main__":
    unittest.main()
