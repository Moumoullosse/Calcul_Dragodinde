# Planificateur Dragodindes v2

Prototype `FastAPI` avec petite interface web, fortement inspire du fichier Excel `dragodindes_auto_v5_selection_pilotee.xlsx`.

## Ce que fait l'application

- saisie du stock males / femelles par dragodinde
- selection automatique avec ordre de croisements proche du classeur
- complement automatique des G1 pour remplir la session
- vues `Selection_auto`, `Tableau_final`, `Recap_creation`, `Controle`, `Ratios_G10`, `Plan_optimal`
- interface HTML simple, sans JavaScript obligatoire

## Lancer l'application

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Puis ouvrir `http://127.0.0.1:8000`.

## Limites actuelles

- la v2 suit beaucoup mieux la structure du classeur, mais n'est pas encore certifiee cellule par cellule
- les ratios G10 sont integres en dur d'apres le tableau Excel
- pour une equivalence totale, il faudra comparer la sortie sur plusieurs stocks reels
