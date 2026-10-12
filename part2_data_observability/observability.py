"""PARTIE 2 : data observability (les 5 piliers).

Principe : on ne code AUCUNE règle métier détaillée ; on mesure en continu la santé des données
(fraîcheur, volume, schéma, distribution, lignage) et on signale ce qui sort de l'ordinaire.
L'observability répond à la question : « y a-t-il quelque chose d'anormal ? »
Cette partie n'utilise PAS Great Expectations.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
RESULTS_DIR = HERE / "results"
DB_PATH = RESULTS_DIR / "observability.db"
RESULTS_DIR.mkdir(exist_ok=True)

EXPECTED_COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id",
    "quantity", "unit_price", "country", "total_amount",
]
PROFILED_COLUMNS = ["order_id", "customer_id", "order_date", "product_id", "quantity", "unit_price"]

# Seuils de démonstration (fixes, à documenter à l'oral)
VOLUME_RANGE = (9_500, 10_500)   # lignes attendues par lot
FRESHNESS_MAX_HOURS = 24         # retard maximal toléré
PRICE_DRIFT_MAX_PCT = 10.0       # dérive max du prix moyen vs dernier lot propre
FALLBACK_BASELINE_PRICE = 255.0  # moyenne théorique d'un tirage uniforme sur [10, 500]


def load_data(batch_name: str) -> pd.DataFrame:
    path = DATA_DIR / f"orders_{batch_name}.csv"
    if not path.exists():
        raise SystemExit(f"Dataset introuvable : {path}. Lancez d'abord generate_data.py (à la racine).")
    return pd.read_csv(path, parse_dates=["order_date"])


def get_price_baseline() -> float | None:
    """Prix moyen du dernier lot propre enregistré (référence pour la dérive de distribution)."""
    if not DB_PATH.exists():
        return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT avg_unit_price FROM observability_metrics "
                "WHERE batch = 'clean' ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        return float(row[0]) if row and row[0] is not None else None
    except sqlite3.Error:
        return None


def collect_metrics(df: pd.DataFrame, batch_name: str) -> dict:
    row_count = len(df)

    # Pilier 1 — Volume
    volume_status = "objectif" if VOLUME_RANGE[0] <= row_count <= VOLUME_RANGE[1] else "alerte"

    # Pilier 2 — Schéma
    missing_columns = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    schema_ok = set(df.columns) == set(EXPECTED_COLUMNS)

    # Pilier 3 — Fraîcheur : retard entre maintenant et la commande la plus récente
    freshness_hours, freshness_status = None, "alerte"
    if "order_date" in df.columns and df["order_date"].notna().any():
        lag = pd.Timestamp.now() - df["order_date"].max()
        freshness_hours = round(max(lag.total_seconds() / 3600, 0.0), 1)
        freshness_status = "objectif" if freshness_hours <= FRESHNESS_MAX_HOURS else "alerte"

    # Pilier 4 — Distribution : dérive du prix moyen vs dernier lot propre
    avg_price = float(df["unit_price"].mean()) if "unit_price" in df.columns else None
    baseline = get_price_baseline() or FALLBACK_BASELINE_PRICE
    price_drift_pct = None
    if avg_price is not None:
        price_drift_pct = round((avg_price - baseline) / baseline * 100, 2) + 0.0
    distribution_status = (
        "alerte" if price_drift_pct is None or abs(price_drift_pct) > PRICE_DRIFT_MAX_PCT else "objectif"
    )

    # Profilage de colonnes (niveau « column-level profiling » de la hiérarchie IBM)
    completeness_values = [float(df[c].notna().mean() * 100) for c in PROFILED_COLUMNS if c in df.columns]
    completeness = sum(completeness_values) / len(completeness_values) if completeness_values else 0.0
    duplicate_order_ids = int(df["order_id"].duplicated().sum()) if "order_id" in df.columns else row_count
    profiling_status = "objectif" if completeness >= 99.9 and duplicate_order_ids == 0 else "alerte"

    # Statut global : critique si le schéma est cassé (casse les traitements aval), alerte si un indicateur dérive
    indicators = [volume_status, freshness_status, distribution_status, profiling_status]
    if not schema_ok:
        status = "critique"
    elif "alerte" in indicators:
        status = "alerte"
    else:
        status = "objectif"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "batch": batch_name,
        "source_file": f"orders_{batch_name}.csv",  # Pilier 5 — lignage minimal
        "row_count": row_count,
        "volume_status": volume_status,
        "schema_ok": schema_ok,
        "missing_columns": ", ".join(missing_columns),
        "freshness_hours": freshness_hours,
        "freshness_status": freshness_status,
        "avg_unit_price": round(avg_price, 2) if avg_price is not None else None,
        "price_drift_pct": price_drift_pct,
        "distribution_status": distribution_status,
        "completeness_pct": round(completeness, 2),
        "duplicate_order_ids": duplicate_order_ids,
        "profiling_status": profiling_status,
        "status": status,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["clean", "corrupted"], required=True)
    parser.add_argument("--reset", action="store_true", help="Supprime l'historique SQLite avant l'exécution")
    args = parser.parse_args()

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()

    df = load_data(args.batch)
    print(f"\n=== PARTIE 2 : DATA OBSERVABILITY — lot {args.batch.upper()} ({len(df):,} lignes) ===\n")

    m = collect_metrics(df, args.batch)
    fresh = f"{m['freshness_hours']} h de retard" if m["freshness_hours"] is not None else "n/a"
    drift = f"{m['price_drift_pct']:+.1f} % (prix moyen)" if m["price_drift_pct"] is not None else "n/a"
    print(f"  Fraîcheur    [{m['freshness_status']:<8}] {fresh}")
    print(f"  Volume       [{m['volume_status']:<8}] {m['row_count']:,} lignes (attendu {VOLUME_RANGE[0]:,}–{VOLUME_RANGE[1]:,})")
    print(f"  Schéma       [{'objectif' if m['schema_ok'] else 'critique':<8}] "
          f"{'conforme' if m['schema_ok'] else 'colonne(s) manquante(s) : ' + m['missing_columns']}")
    print(f"  Distribution [{m['distribution_status']:<8}] {drift}")
    print(f"  Lignage      [{'objectif':<8}] source : {m['source_file']}")
    print(f"  Profilage    [{m['profiling_status']:<8}] complétude {m['completeness_pct']} %, "
          f"{m['duplicate_order_ids']} doublons d'order_id")
    print(f"\nStatut global : {m['status'].upper()}")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            pd.DataFrame([m]).to_sql("observability_metrics", conn, if_exists="append", index=False)
    except Exception as exc:
        raise SystemExit(f"Erreur SQLite ({exc}). Ancienne base au schéma différent ? Relancez avec --reset.")
    (RESULTS_DIR / f"metrics_{args.batch}.json").write_text(
        json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSQLite : {DB_PATH.relative_to(HERE)}  |  Dashboard : streamlit run dashboard.py")


if __name__ == "__main__":
    main()
