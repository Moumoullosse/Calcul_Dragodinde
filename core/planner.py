from __future__ import annotations

from dataclasses import dataclass

from .data import (
    AUTO_FILL_G1,
    BREEDS,
    BREED_BY_NAME,
    RATIO_BY_NAME,
    RECAP_NOTES,
    SELECTION_ORDER,
    SESSION_INDIVIDUAL_CAPACITY,
    SESSION_PAIR_CAPACITY,
)


@dataclass
class StockEntry:
    males: int = 0
    females: int = 0

    @property
    def pairs(self) -> int:
        return min(self.males, self.females)


@dataclass
class SelectionRow:
    target: str
    generation: int
    parent1: str
    parent2: str
    remaining_pairs_before: int
    p1_m_remaining: int
    p1_f_remaining: int
    p2_m_remaining: int
    p2_f_remaining: int
    option_a: int
    option_b: int
    chosen_mode: str
    pairs_created: int
    p1_m_used: int
    p1_f_used: int
    p2_m_used: int
    p2_f_used: int
    individuals_used: int


def _empty_stock() -> dict[str, StockEntry]:
    return {breed.name: StockEntry() for breed in BREEDS}


def _build_ratio_rows() -> list[dict[str, object]]:
    rows = []
    for breed in reversed(BREEDS[:-1]):
        ratio = RATIO_BY_NAME[breed.name]
        rows.append(
            {
                "Dragodinde": breed.name,
                "Gen": breed.generation,
                "Occurrences pour 1 G10": breed.ratio_occurrences,
                "% cible individus": ratio,
                "Paires cibles sur 125": round(ratio * SESSION_PAIR_CAPACITY),
                "Individus cibles sur 250": round(ratio * SESSION_INDIVIDUAL_CAPACITY),
            }
        )
    return rows


def _target_pairs_for_capacity(capacity_pairs: int) -> dict[str, int]:
    targets: dict[str, int] = {}
    for breed in BREEDS:
        if breed.generation <= 1:
            continue
        targets[breed.name] = max(0, round(RATIO_BY_NAME[breed.name] * capacity_pairs))
    return targets


def _allocate_weighted_pairs(
    capacity_pairs: int,
    weights: dict[str, int],
    caps: dict[str, int] | None = None,
) -> dict[str, int]:
    allocations = {name: 0 for name in weights}
    remaining_pairs = max(0, capacity_pairs)
    active = {
        name
        for name, weight in weights.items()
        if weight > 0 and (caps is None or caps.get(name, 0) > 0)
    }

    while remaining_pairs > 0 and active:
        total_weight = sum(weights[name] for name in active)
        if total_weight <= 0:
            break

        assigned_this_round = 0
        remainders: list[tuple[float, str]] = []

        for name in active:
            remaining_cap = caps.get(name, remaining_pairs) - allocations[name] if caps is not None else remaining_pairs
            if remaining_cap <= 0:
                continue
            raw_share = remaining_pairs * weights[name] / total_weight
            whole_share = min(remaining_cap, int(raw_share))
            if whole_share > 0:
                allocations[name] += whole_share
                assigned_this_round += whole_share
            remainders.append((raw_share - int(raw_share), name))

        remaining_pairs -= assigned_this_round
        active = {
            name
            for name in active
            if caps is None or allocations[name] < caps.get(name, 0)
        }

        if remaining_pairs <= 0 or not active:
            break

        assigned_by_remainder = 0
        for _, name in sorted(remainders, reverse=True):
            if name not in active or remaining_pairs <= 0:
                continue
            allocations[name] += 1
            remaining_pairs -= 1
            assigned_by_remainder += 1
            if caps is not None and allocations[name] >= caps.get(name, 0):
                active.discard(name)

        if assigned_this_round == 0 and assigned_by_remainder == 0:
            break

    return allocations


def _target_pairs_for_stock_balance(
    stock: dict[str, StockEntry],
    capacity_pairs: int,
) -> dict[str, int]:
    base_targets = _target_pairs_for_capacity(capacity_pairs)
    targets = {name: 0 for name in base_targets}

    for generation in sorted({breed.generation for breed in BREEDS if breed.generation > 1}):
        generation_breeds = [breed for breed in BREEDS if breed.generation == generation]
        generation_total = sum(base_targets.get(breed.name, 0) for breed in generation_breeds)
        if generation_total <= 0:
            continue

        deficits = {}
        for breed in generation_breeds:
            target_stock_pairs = round(RATIO_BY_NAME[breed.name] * SESSION_PAIR_CAPACITY)
            current_stock_pairs = stock.get(breed.name, StockEntry()).pairs
            deficits[breed.name] = max(0, target_stock_pairs - current_stock_pairs)

        if sum(deficits.values()) <= 0:
            generation_targets = {
                breed.name: base_targets.get(breed.name, 0)
                for breed in generation_breeds
            }
        else:
            generation_targets = _allocate_weighted_pairs(generation_total, deficits)

        for breed in generation_breeds:
            targets[breed.name] = generation_targets.get(breed.name, 0)

    return targets


def _build_auto_fill_pairs(missing_pairs: int) -> dict[str, int]:
    total_weight = sum(AUTO_FILL_G1.values())
    values: dict[str, int] = {}
    assigned = 0
    items = list(AUTO_FILL_G1.items())
    for index, (name, weight) in enumerate(items):
        if index == len(items) - 1:
            pairs = missing_pairs - assigned
        else:
            pairs = int(missing_pairs * weight / total_weight)
            assigned += pairs
        values[name] = max(0, pairs)
    return values


def _compute_usage_map(selection_rows: list[SelectionRow]) -> dict[str, dict[str, int]]:
    usage = {breed.name: {"males": 0, "females": 0} for breed in BREEDS}
    for row in selection_rows:
        usage[row.parent1]["males"] += row.p1_m_used
        usage[row.parent1]["females"] += row.p1_f_used
        usage[row.parent2]["males"] += row.p2_m_used
        usage[row.parent2]["females"] += row.p2_f_used
    return usage


def plan_session(
    stock: dict[str, StockEntry],
    session_capacity: int = SESSION_INDIVIDUAL_CAPACITY,
    include_auto_fill_g1: bool = True,
    balance_by_existing_stock: bool = False,
) -> dict[str, object]:
    capacity_pairs = max(session_capacity // 2, 0)
    available = {name: StockEntry(entry.males, entry.females) for name, entry in stock.items()}
    if balance_by_existing_stock:
        target_pairs_by_breed = _target_pairs_for_stock_balance(stock, capacity_pairs)
    else:
        target_pairs_by_breed = _target_pairs_for_capacity(capacity_pairs)

    selection_rows: list[SelectionRow] = []
    remaining_pairs_before = capacity_pairs

    for target_name in SELECTION_ORDER:
        breed = BREED_BY_NAME[target_name]
        parent1_name = breed.parent1 or ""
        parent2_name = breed.parent2 or ""
        parent1 = available[parent1_name]
        parent2 = available[parent2_name]
        remaining_target_pairs = target_pairs_by_breed.get(target_name, 0)

        while remaining_pairs_before > 0 and remaining_target_pairs > 0:
            p1_m_remaining = parent1.males
            p1_f_remaining = parent1.females
            p2_m_remaining = parent2.males
            p2_f_remaining = parent2.females

            option_a = max(0, min(remaining_pairs_before, remaining_target_pairs, p1_f_remaining, p2_m_remaining))
            option_b = max(0, min(remaining_pairs_before, remaining_target_pairs, p1_m_remaining, p2_f_remaining))

            if option_a <= 0 and option_b <= 0:
                break

            if option_a >= option_b:
                chosen_mode = "P1F + P2M"
                pairs_created = option_a
                p1_m_used = 0
                p1_f_used = pairs_created
                p2_m_used = pairs_created
                p2_f_used = 0
            else:
                chosen_mode = "P1M + P2F"
                pairs_created = option_b
                p1_m_used = pairs_created
                p1_f_used = 0
                p2_m_used = 0
                p2_f_used = pairs_created

            parent1.males -= p1_m_used
            parent1.females -= p1_f_used
            parent2.males -= p2_m_used
            parent2.females -= p2_f_used

            selection_rows.append(
                SelectionRow(
                    target=target_name,
                    generation=breed.generation,
                    parent1=parent1_name,
                    parent2=parent2_name,
                    remaining_pairs_before=remaining_pairs_before,
                    p1_m_remaining=p1_m_remaining,
                    p1_f_remaining=p1_f_remaining,
                    p2_m_remaining=p2_m_remaining,
                    p2_f_remaining=p2_f_remaining,
                    option_a=option_a,
                    option_b=option_b,
                    chosen_mode=chosen_mode,
                    pairs_created=pairs_created,
                    p1_m_used=p1_m_used,
                    p1_f_used=p1_f_used,
                    p2_m_used=p2_m_used,
                    p2_f_used=p2_f_used,
                    individuals_used=pairs_created * 2,
                )
            )
            remaining_pairs_before = max(0, remaining_pairs_before - pairs_created)
            remaining_target_pairs = max(0, remaining_target_pairs - pairs_created)

    planned_pairs = sum(row.pairs_created for row in selection_rows)
    auto_fill_pairs = max(0, capacity_pairs - planned_pairs) if include_auto_fill_g1 else 0
    auto_fill = _build_auto_fill_pairs(auto_fill_pairs) if include_auto_fill_g1 else {}
    usage_map = _compute_usage_map(selection_rows)
    total_individuals = planned_pairs * 2 + auto_fill_pairs * 2

    final_rows = []
    for breed in BREEDS:
        stock_entry = stock.get(breed.name, StockEntry())
        used_males = usage_map[breed.name]["males"]
        used_females = usage_map[breed.name]["females"]
        auto_add = auto_fill.get(breed.name, 0)
        males_total = used_males + auto_add
        females_total = used_females + auto_add
        individuals = males_total + females_total
        target_ratio = RATIO_BY_NAME[breed.name]
        current_ratio = individuals / total_individuals if total_individuals else 0.0
        base_target_pairs = round(target_ratio * capacity_pairs)
        adjusted_target_pairs = target_pairs_by_breed.get(breed.name, base_target_pairs)
        final_rows.append(
            {
                "Dragodinde": breed.name,
                "Gen": breed.generation,
                "Males stock": stock_entry.males,
                "Femelles stock": stock_entry.females,
                "Males pris du stock": used_males,
                "Femelles prises du stock": used_females,
                "Males ajoutes G1": auto_add,
                "Femelles ajoutees G1": auto_add,
                "Males a prendre total": males_total,
                "Femelles a prendre total": females_total,
                "Total individus": individuals,
                "% cible G10": target_ratio,
                "% selection actuelle": current_ratio,
                "Ecart vs cible": current_ratio - target_ratio,
                "Paires cibles ratio session": base_target_pairs,
                "Paires cibles": adjusted_target_pairs,
                "Ecart paires": (individuals // 2) - adjusted_target_pairs,
                "Paires stock": stock_entry.pairs,
                "Paires cibles G10": round(target_ratio * SESSION_PAIR_CAPACITY),
                "Paires reco stock": 0 if breed.generation == 1 else min(stock_entry.pairs, round(target_ratio * SESSION_PAIR_CAPACITY)),
                "Individus reco stock": 0 if breed.generation == 1 else min(stock_entry.pairs, round(target_ratio * SESSION_PAIR_CAPACITY)) * 2,
                "Ecart paires stock vs cible": stock_entry.pairs - round(target_ratio * SESSION_PAIR_CAPACITY),
                "Regle": "Auto-fill G1 seulement" if breed.generation == 1 else ("Equilibrage selon stock existant" if balance_by_existing_stock else "Prendre selon stock/cible"),
            }
        )

    recap_creation_rows = [
        {
            "Dragodinde creee": row.target,
            "Gen": row.generation,
            "Parent 1": row.parent1,
            "Parent 2": row.parent2,
            "Mode retenu": row.chosen_mode,
            "Paires creees": row.pairs_created,
            "Individus parents utilises": row.individuals_used,
            "Notes": RECAP_NOTES.get(row.target, ""),
        }
        for row in selection_rows
    ]

    selection_generation_summary = []
    final_generation_summary = []
    tableau_generation_summary = []
    for generation in range(10, 0, -1):
        selection_individuals = sum(
            row.pairs_created * 2
            for row in selection_rows
            if row.generation == generation
        )
        selection_generation_summary.append(
            {
                "Generation": generation,
                "Individus a prendre": selection_individuals,
                "Paires": selection_individuals // 2,
            }
        )
        created_pairs = sum(
            row.pairs_created
            for row in selection_rows
            if row.generation == generation
        )
        final_generation_summary.append(
            {
                "Generation": generation,
                "Dragodindes creees": created_pairs,
            }
        )
        tableau_individuals = sum(
            row["Total individus"]
            for row in final_rows
            if row["Gen"] == generation
        )
        tableau_generation_summary.append(
            {
                "Generation": generation,
                "Individus a prendre": tableau_individuals,
                "Paires": tableau_individuals // 2,
            }
        )

    controls = {
        "Individus planifies depuis croisements": planned_pairs * 2,
        "Paires G1 ajoutees": auto_fill_pairs,
        "Individus ajoutes G1": auto_fill_pairs * 2,
        "Total individus a prendre": total_individuals,
        "Objectif": session_capacity,
        "Ecart": total_individuals - session_capacity,
    }

    plan_rows = [
        {
            "Dragodinde": row["Dragodinde"],
            "Gen": row["Gen"],
            "Males a prendre": f'{row["Males a prendre total"]}/{row["Males stock"]}',
            "Femelles a prendre": f'{row["Femelles a prendre total"]}/{row["Femelles stock"]}',
            "Paires prises": row["Total individus"] // 2,
            "Source": "Auto-fill G1" if row["Gen"] == 1 else "Stock reel",
            "% cible G10": row["% cible G10"],
            "Commentaire": "Complement auto G1 uniquement" if row["Gen"] == 1 else "Limite au stock dispo",
        }
        for row in final_rows
        if row["Total individus"] > 0
    ]

    ratios_rows = _build_ratio_rows()

    return {
        "selection_rows": selection_rows,
        "selection_generation_summary": selection_generation_summary,
        "final_rows": final_rows,
        "tableau_generation_summary": tableau_generation_summary,
        "recap_creation_rows": recap_creation_rows,
        "final_generation_summary": final_generation_summary,
        "controls": controls,
        "plan_rows": plan_rows,
        "ratios_rows": ratios_rows,
        "auto_fill_pairs": auto_fill_pairs,
        "auto_fill_breakdown": auto_fill,
        "include_auto_fill_g1": include_auto_fill_g1,
        "balance_by_existing_stock": balance_by_existing_stock,
        "session_capacity": session_capacity,
        "capacity_pairs": capacity_pairs,
    }


def default_stock() -> dict[str, StockEntry]:
    return _empty_stock()


def breed_names() -> list[str]:
    return [breed.name for breed in BREEDS]


def breed_generation(name: str) -> int:
    return BREED_BY_NAME[name].generation
