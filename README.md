# Qualité des données : Great Expectations vs Data Observability

Projet académique individuel, volontairement séparé en **deux parties indépendantes** pour ne pas
confondre les deux approches. Elles partagent seulement les données générées par `generate_data.py`.

| | Partie 1 — Great Expectations | Partie 2 — Data observability |
|---|---|---|
| Dossier | `part1_great_expectations/` | `part2_data_observability/` |
| Approche | Règles explicites, écrites à l'avance | Mesure continue, détection d'écarts |
| Question | « Mes règles sont-elles respectées ? » | « Y a-t-il quelque chose d'anormal ? » |
| Livrable | Checkpoint + Data Docs (HTML) | Métriques SQLite + dashboard |

## Corruptions injectées dans le lot « corrupted »

| Corruption | Partie 1 (GX) | Partie 2 (observability) |
|---|:-:|:-:|
| 150 `customer_id` manquants | détecté | détecté (profilage) |
| 100 `order_id` dupliqués | détecté | détecté (profilage) |
| Colonne `country` supprimée | détecté | détecté (schéma) |
| 40 % des lignes supprimées | **non** | détecté (volume) |
| Données vieilles de 3 jours | **non** | détecté (fraîcheur) |
| Prix ÷ 2 sur 30 % des lignes | **non** | détecté (distribution) |

## Démarrage rapide (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r part1_great_expectations\requirements.txt -r part2_data_observability\requirements.txt
python generate_data.py
```

Puis suivre le README de chaque partie, ou lancer `run_demo.bat` pour tout enchaîner.

> Le lot propre est généré pour finir « maintenant » : relancez `generate_data.py` avant une démo
> (sinon, après 24 h, l'alerte de fraîcheur se déclencherait aussi sur le lot propre).
