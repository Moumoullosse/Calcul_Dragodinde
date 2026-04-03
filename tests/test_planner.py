import unittest

from core.data import RATIO_BY_NAME, SESSION_PAIR_CAPACITY
from core.planner import default_stock, plan_session


class PlanSessionGenerationBalancingTests(unittest.TestCase):
    def test_pourpre_does_not_consume_all_capacity_before_indigo(self) -> None:
        stock = default_stock()

        # Both targets are feasible, but Pourpre appears earlier in SELECTION_ORDER.
        # The planner must still leave room for Indigo according to the target ratios.
        for breed_name in ("Amande-Dore", "Amande-Rousse", "Ebene-Indigo"):
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = {
            row["Dragodinde creee"]: row["Paires creees"]
            for row in results["recap_creation_rows"]
        }

        capacity_pairs = 250 // 2
        expected_indigo_pairs = round(RATIO_BY_NAME["Indigo"] * capacity_pairs)
        expected_pourpre_pairs = round(RATIO_BY_NAME["Pourpre"] * capacity_pairs)

        self.assertEqual(created_pairs.get("Pourpre"), expected_pourpre_pairs)
        self.assertEqual(created_pairs.get("Indigo"), expected_indigo_pairs)
        self.assertGreater(created_pairs.get("Indigo", 0), 0)

    def test_all_generations_respect_targets_with_abundant_stock(self) -> None:
        stock = default_stock()

        for breed_name in stock:
            stock[breed_name].males = 500
            stock[breed_name].females = 500

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = {
            row["Dragodinde creee"]: row["Paires creees"]
            for row in results["recap_creation_rows"]
        }

        capacity_pairs = 250 // 2

        expected_targets = {
            breed_name: round(ratio * capacity_pairs)
            for breed_name, ratio in RATIO_BY_NAME.items()
            if breed_name not in {"Amande", "Dore", "Rousse", "Prune-Emeraude"}
        }

        for breed_name, expected_pairs in expected_targets.items():
            with self.subTest(breed=breed_name):
                self.assertEqual(created_pairs.get(breed_name, 0), expected_pairs)

    def test_constrained_shared_parent_still_allows_multiple_breeds(self) -> None:
        stock = default_stock()

        # Amande-Rousse is the constrained shared parent between Indigo and Pourpre.
        stock["Amande-Rousse"].males = 3
        stock["Amande-Rousse"].females = 3

        # The other parents are abundant, so the bottleneck is really the shared breed.
        for breed_name in ("Amande-Dore", "Ebene-Indigo"):
            stock[breed_name].males = 200
            stock[breed_name].females = 200

        results = plan_session(
            stock,
            session_capacity=250,
            include_auto_fill_g1=False,
        )

        created_pairs = {
            row["Dragodinde creee"]: row["Paires creees"]
            for row in results["recap_creation_rows"]
        }

        final_rows = {
            row["Dragodinde"]: row
            for row in results["final_rows"]
        }

        self.assertEqual(created_pairs.get("Pourpre", 0), 3)
        self.assertEqual(created_pairs.get("Indigo", 0), 3)
        self.assertGreater(created_pairs.get("Pourpre", 0), 0)
        self.assertGreater(created_pairs.get("Indigo", 0), 0)

        amande_rousse = final_rows["Amande-Rousse"]
        self.assertEqual(amande_rousse["Males a prendre total"], 3)
        self.assertEqual(amande_rousse["Femelles a prendre total"], 3)

    def test_stock_balancing_reduces_creation_for_already_stocked_breed(self) -> None:
        stock = default_stock()

        for breed_name in ("Amande-Dore", "Amande-Rousse", "Ebene-Indigo"):
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

        created_pairs = {
            row["Dragodinde creee"]: row["Paires creees"]
            for row in results["recap_creation_rows"]
        }
        final_rows = {
            row["Dragodinde"]: row
            for row in results["final_rows"]
        }

        self.assertEqual(created_pairs.get("Pourpre", 0), 0)
        self.assertEqual(final_rows["Pourpre"]["Paires cibles"], 0)
        self.assertGreaterEqual(created_pairs.get("Indigo", 0), 1)

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


if __name__ == "__main__":
    unittest.main()
