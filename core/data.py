from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Breed:
    name: str
    generation: int
    parent1: str | None = None
    parent2: str | None = None
    ratio_occurrences: int = 0


SESSION_INDIVIDUAL_CAPACITY = 250
SESSION_PAIR_CAPACITY = SESSION_INDIVIDUAL_CAPACITY // 2

AUTO_FILL_G1 = {
    "Amande": 79,
    "Dore": 79,
    "Rousse": 66,
}

BREEDS: list[Breed] = [
    Breed("Amande", 1, ratio_occurrences=79),
    Breed("Dore", 1, ratio_occurrences=79),
    Breed("Rousse", 1, ratio_occurrences=66),
    Breed("Amande-Rousse", 2, "Amande", "Rousse", 33),
    Breed("Amande-Dore", 2, "Amande", "Dore", 46),
    Breed("Dore-Rousse", 2, "Dore", "Rousse", 33),
    Breed("Ebene", 3, "Amande-Dore", "Dore-Rousse", 23),
    Breed("Indigo", 3, "Amande-Dore", "Amande-Rousse", 23),
    Breed("Ebene-Indigo", 4, "Ebene", "Indigo", 20),
    Breed("Pourpre", 5, "Amande-Rousse", "Ebene-Indigo", 10),
    Breed("Orchidee", 5, "Dore-Rousse", "Ebene-Indigo", 10),
    Breed("Ebene-Orchidee", 6, "Ebene", "Orchidee", 3),
    Breed("Orchidee-Pourpre", 6, "Orchidee", "Pourpre", 6),
    Breed("Indigo-Pourpre", 6, "Indigo", "Pourpre", 3),
    Breed("Turquoise", 7, "Ebene-Orchidee", "Orchidee-Pourpre", 3),
    Breed("Ivoire", 7, "Indigo-Pourpre", "Orchidee-Pourpre", 3),
    Breed("Ivoire-Turquoise", 8, "Ivoire", "Turquoise", 2),
    Breed("Ivoire-Pourpre", 8, "Ivoire", "Pourpre", 1),
    Breed("Turquoise-Orchidee", 8, "Turquoise", "Orchidee", 1),
    Breed("Prune", 9, "Ivoire-Turquoise", "Turquoise-Orchidee", 1),
    Breed("Emeraude", 9, "Ivoire-Turquoise", "Ivoire-Pourpre", 1),
    Breed("Prune-Emeraude", 10, "Prune", "Emeraude", 0),
]

SELECTION_ORDER = [
    "Prune-Emeraude",
    "Prune",
    "Emeraude",
    "Ivoire-Turquoise",
    "Ivoire-Pourpre",
    "Turquoise-Orchidee",
    "Turquoise",
    "Ivoire",
    "Ebene-Orchidee",
    "Orchidee-Pourpre",
    "Indigo-Pourpre",
    "Pourpre",
    "Orchidee",
    "Ebene-Indigo",
    "Ebene",
    "Indigo",
    "Amande-Rousse",
    "Amande-Dore",
    "Dore-Rousse",
]

RECAP_NOTES = {
    "Prune-Emeraude": "Correction des erreurs 522 : suppression des formules auto-referentes.",
    "Prune": "La planification est gloutonne : G10 vers G2.",
    "Emeraude": "Parents partages comptes une seule fois.",
    "Ivoire-Turquoise": "Le manque jusqu'a 250 individus est complete par Amande / Dore / Rousse.",
}

TOTAL_RATIO_OCCURRENCES = sum(breed.ratio_occurrences for breed in BREEDS)
RATIO_BY_NAME = {
    breed.name: (breed.ratio_occurrences / TOTAL_RATIO_OCCURRENCES if TOTAL_RATIO_OCCURRENCES else 0.0)
    for breed in BREEDS
}
BREED_BY_NAME = {breed.name: breed for breed in BREEDS}
