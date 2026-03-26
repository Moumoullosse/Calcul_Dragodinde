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

## Deployer sur Render

Le projet contient un fichier `render.yaml` pour faciliter le deploiement.

1. Cree un depot GitHub et pousse ce projet dessus.
2. Cree un compte sur Render et connecte ton compte GitHub.
3. Dans Render, clique sur `New` puis `Blueprint`.
4. Selectionne le depot `Dragodinde`.
5. Render detectera automatiquement le fichier `render.yaml`.
6. Lance le deploiement.

Configuration utilisee :

- build command : `pip install -r requirements.txt`
- start command : `uvicorn main:app --host 0.0.0.0 --port $PORT`

Une fois le deploy termine, Render te donnera une URL publique en `onrender.com`.

Notes :

- le premier chargement peut etre lent si tu utilises l'offre gratuite
- a chaque `git push`, Render peut redeployer automatiquement l'application

## Limites actuelles

- la v2 suit beaucoup mieux la structure du classeur, mais n'est pas encore certifiee cellule par cellule
- les ratios G10 sont integres en dur d'apres le tableau Excel
- pour une equivalence totale, il faudra comparer la sortie sur plusieurs stocks reels
