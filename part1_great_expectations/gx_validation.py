"""PARTIE 1 : validation des données avec Great Expectations.

Principe : des règles (Expectations) écrites à l'avance, exécutées par un Checkpoint.
GX répond à la question : « les données respectent-elles MES règles ? »
Cette partie n'utilise AUCUNE métrique d'observability (ni base SQLite, ni dashboard).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
RESULTS_DIR = HERE / "results"
GX_DIR = HERE / "gx_project"
RESULTS_DIR.mkdir(exist_ok=True)

EXPECTED_COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id",
    "quantity", "unit_price", "country", "total_amount",
]


def load_data(batch_name: str) -> pd.DataFrame:
    path = DATA_DIR / f"orders_{batch_name}.csv"
    if not path.exists():
        raise SystemExit(f"Dataset introuvable : {path}. Lancez d'abord generate_data.py (à la racine).")
    return pd.read_csv(path, parse_dates=["order_date"])


def run_checkpoint(df: pd.DataFrame) -> dict:
    """Suite d'Expectations -> Validation Definition -> Checkpoint -> Data Docs."""
    context = gx.get_context(mode="file", project_root_dir=str(GX_DIR))

    data_source = context.data_sources.add_or_update_pandas(name="orders_source")
    try:
        asset = data_source.get_asset("orders")
    except Exception:
        asset = data_source.add_dataframe_asset(name="orders")
    try:
        batch_definition = asset.get_batch_definition("whole_batch")
    except Exception:
        batch_definition = asset.add_batch_definition_whole_dataframe("whole_batch")

    # Les règles : une par dimension de qualité
    expectations = [
        gxe.ExpectTableColumnsToMatchSet(column_set=EXPECTED_COLUMNS, exact_match=True),  # schéma
        gxe.ExpectColumnValuesToNotBeNull(column="customer_id"),                          # complétude
        gxe.ExpectColumnValuesToBeUnique(column="order_id"),                              # unicité
        gxe.ExpectColumnValuesToBeBetween(column="quantity", min_value=1, max_value=7),   # validité
        gxe.ExpectColumnValuesToBeBetween(column="unit_price", min_value=0, max_value=500),
        gxe.ExpectColumnValuesToNotBeNull(column="order_date"),
    ]
    suite = context.suites.add_or_update(
        gx.ExpectationSuite(name="ecommerce_quality_suite", expectations=expectations)
    )
    validation_definition = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(name="orders_validation", data=batch_definition, suite=suite)
    )
    checkpoint = context.checkpoints.add_or_update(
        gx.Checkpoint(
            name="orders_checkpoint",
            validation_definitions=[validation_definition],
            actions=[gx.checkpoint.UpdateDataDocsAction(name="update_data_docs")],
        )
    )

    with contextlib.redirect_stderr(io.StringIO()):  # masque la barre de progression
        checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})

    suite_result = next(iter(checkpoint_result.run_results.values()))
    results = []
    for item in suite_result.results:
        result = item.result or {}
        column = (item.expectation_config.kwargs or {}).get("column", "(table)")
        results.append(
            {
                "expectation_type": item.expectation_config.type,
                "column": column,
                "success": bool(item.success),
                "unexpected_count": int(result.get("unexpected_count", 0) or 0),
                "unexpected_percent": round(float(result.get("unexpected_percent", 0) or 0), 2),
            }
        )

    docs_index = GX_DIR / "gx" / "uncommitted" / "data_docs" / "local_site" / "index.html"
    return {
        "success": bool(checkpoint_result.success),
        "passed": sum(r["success"] for r in results),
        "total": len(results),
        "data_docs_url": docs_index.as_uri() if docs_index.exists() else None,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", choices=["clean", "corrupted"], required=True)
    parser.add_argument(
        "--strict", action="store_true",
        help="Code de sortie 1 si la validation échoue (le lot est bloqué avant chargement)",
    )
    args = parser.parse_args()

    df = load_data(args.batch)
    print(f"\n=== PARTIE 1 : GREAT EXPECTATIONS — lot {args.batch.upper()} ({len(df):,} lignes) ===\n")

    validation = run_checkpoint(df)

    for r in validation["results"]:
        flag = "PASS" if r["success"] else "FAIL"
        print(f"  [{flag}] {r['expectation_type']:<42} {r['column']:<12} valeurs fautives : {r['unexpected_count']}")

    print(f"\nRésultat : {validation['passed']}/{validation['total']} règles validées "
          f"-> {'SUCCÈS' if validation['success'] else 'ÉCHEC'}")

    out = RESULTS_DIR / f"validation_{args.batch}.json"
    out.write_text(json.dumps({"batch": args.batch, **validation}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON      : {out.relative_to(HERE)}")
    if validation["data_docs_url"]:
        print(f"Data Docs : {validation['data_docs_url']}")

    if args.strict and not validation["success"]:
        print("\nSTRICT : validation en échec, lot bloqué.")
        sys.exit(1)


if __name__ == "__main__":
    main()
