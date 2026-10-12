# Partie 1 — Great Expectations (data testing)

**Question posée : « les données respectent-elles MES règles ? »**

Des règles (Expectations) sont écrites **à l'avance** et exécutées par un **Checkpoint**.
GX ne détecte que ce qui a été prévu.

```text
CSV → Expectation Suite → Validation → Checkpoint → Data Docs (rapport HTML)
```

Pas de SQLite, pas de dashboard, pas de métriques de surveillance : tout cela est dans la partie 2.

## Utilisation

```powershell
pip install -r requirements.txt
cd ..                                   # à la racine : python generate_data.py
python generate_data.py
python part1_great_expectations\gx_validation.py --batch clean
python part1_great_expectations\gx_validation.py --batch corrupted
```

`--strict` : code de sortie 1 si la validation échoue (blocage du lot avant chargement, utilisable dans Airflow/CI).

## Les règles (une par dimension de qualité)

| Dimension | Expectation |
|---|---|
| Schéma | `ExpectTableColumnsToMatchSet` |
| Complétude | `ExpectColumnValuesToNotBeNull` (`customer_id`, `order_date`) |
| Unicité | `ExpectColumnValuesToBeUnique` (`order_id`) |
| Validité | `ExpectColumnValuesToBeBetween` (`quantity` 1–7, `unit_price` 0–500) |

## Résultat attendu

| Lot | Règles validées | Détail |
|---|---|---|
| clean | 6/6 | succès |
| corrupted | 3/6 | échec : schéma, `customer_id` nuls, `order_id` dupliqués |

**Point clé de la démo :** sur le lot corrompu, GX **ne voit pas** la chute de volume, le retard de 3 jours
ni la dérive des prix, car aucune règle n'a été écrite pour ça (les prix restent dans la plage 0–500).
C'est exactement ce que la partie 2 détecte.

Note : GX compte les deux membres de chaque paire de doublons (78 valeurs « inattendues »), alors que
`pandas.duplicated()` ne compte que les répétitions (39).

Les Data Docs sont dans `gx_project/gx/uncommitted/data_docs/local_site/index.html` (chemin affiché à la fin).
