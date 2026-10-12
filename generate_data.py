"""Génère deux lots e-commerce (partagés par les deux parties du projet) : un lot propre et un lot corrompu.

Corruptions injectées dans le lot corrompu :
  1. 150 valeurs manquantes sur customer_id          (complétude -> GX l'attrape)
  2. 100 order_id dupliqués                           (unicité    -> GX l'attrape)
  3. colonne `country` supprimée                      (schéma     -> GX + observability)
  4. 40 % des lignes supprimées                       (volume     -> observability seulement)
  5. données vieilles de 3 jours                      (fraîcheur  -> observability seulement)
  6. prix divisés par 2 sur 30 % des lignes           (distribution -> observability seulement,
                                                       les valeurs restent dans la plage GX)
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

N = 10_000

customer_ids = [f"C{n:05d}" for n in RNG.integers(1, 2500, size=N)]
product_ids = [f"P{n:04d}" for n in RNG.integers(1, 501, size=N)]
countries = RNG.choice(
    ["Morocco", "France", "Spain", "Belgium", "Germany"],
    size=N,
    p=[0.45, 0.20, 0.15, 0.10, 0.10],
)

# Le lot propre se termine "maintenant" : il est donc frais au moment de la démo.
now = pd.Timestamp.now().floor("h")

df = pd.DataFrame(
    {
        "order_id": [f"O{n:06d}" for n in range(1, N + 1)],
        "customer_id": customer_ids,
        "order_date": pd.date_range(end=now, periods=N, freq="h"),
        "product_id": product_ids,
        "quantity": RNG.integers(1, 8, size=N),
        "unit_price": np.round(RNG.uniform(10, 500, size=N), 2),
        "country": countries,
    }
)
df["total_amount"] = np.round(df["quantity"] * df["unit_price"], 2)

clean_path = DATA_DIR / "orders_clean.csv"
df.to_csv(clean_path, index=False)

corrupted = df.copy()

# 1) Valeurs manquantes
null_idx = RNG.choice(corrupted.index, size=150, replace=False)
corrupted.loc[null_idx, "customer_id"] = pd.NA

# 2) order_id dupliqués (on copie l'id de la ligne précédente ; on évite l'indice 0)
duplicate_idx = RNG.choice(corrupted.index[1:], size=100, replace=False)
corrupted.loc[duplicate_idx, "order_id"] = corrupted.loc[
    duplicate_idx - 1, "order_id"
].to_numpy()

# 6) Dérive de distribution : prix /2 sur 30 % des lignes (reste entre 0 et 500)
drift_idx = RNG.choice(corrupted.index, size=int(0.30 * N), replace=False)
corrupted.loc[drift_idx, "unit_price"] = np.round(
    corrupted.loc[drift_idx, "unit_price"] / 2, 2
)
corrupted["total_amount"] = np.round(corrupted["quantity"] * corrupted["unit_price"], 2)

# 5) Données périmées : tout est décalé de 3 jours
corrupted["order_date"] = corrupted["order_date"] - pd.Timedelta(days=3)

# 4) Chute de volume : on garde 60 % des lignes
corrupted = corrupted.sample(frac=0.6, random_state=42).sort_index()

# 3) Colonne attendue supprimée
corrupted = corrupted.drop(columns=["country"])

corrupted_path = DATA_DIR / "orders_corrupted.csv"
corrupted.to_csv(corrupted_path, index=False)

print(f"Clean dataset      : {clean_path.name} ({len(df):,} lignes)")
print(f"Corrupted dataset  : {corrupted_path.name} ({len(corrupted):,} lignes)")
print("Corruptions        : nulls, doublons, colonne supprimée, volume -40 %, données périmées, dérive des prix")
