# Partie 2 — Data observability

**Question posée : « y a-t-il quelque chose d'anormal ? »**

On n'écrit pas de règles métier détaillées : on **mesure en continu** la santé des données et on signale
les écarts. Cette partie n'utilise pas Great Expectations.

```text
CSV → Collecte des métriques (5 piliers) → SQLite → Dashboard Streamlit
```

## Les 5 piliers

| Pilier | Métrique | Seuil de démo |
|---|---|---|
| Fraîcheur | retard de la commande la plus récente | ≤ 24 h |
| Volume | nombre de lignes du lot | 9 500 – 10 500 |
| Schéma | colonnes présentes vs attendues | identique |
| Distribution | dérive du prix moyen vs dernier lot propre | ±10 % |
| Lignage | fichier source enregistré avec chaque métrique | (minimal) |

Un **profilage de colonnes** (complétude, doublons) complète les piliers.
Statut : **critique** si le schéma est cassé, **alerte** si un indicateur dérive, **objectif** sinon.

## Utilisation

```powershell
pip install -r requirements.txt
cd ..
python generate_data.py
python part2_data_observability\observability.py --batch clean --reset
python part2_data_observability\observability.py --batch corrupted
streamlit run part2_data_observability\dashboard.py
```

## Résultat attendu

| Lot | Statut | Détail |
|---|---|---|
| clean | objectif | tous les piliers verts |
| corrupted | critique | schéma cassé ; volume −40 % ; 73 h de retard ; prix moyen −15 % |

Limites : seuils fixes (pas de détection d'anomalies statistique), SQLite à la place d'un entrepôt.
Pistes : comparaison à un historique glissant, OpenLineage pour le lignage, Airflow.
