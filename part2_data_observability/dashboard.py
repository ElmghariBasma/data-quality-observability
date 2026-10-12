from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).resolve().parent / "results" / "observability.db"

st.set_page_config(page_title="Data Observability Monitor", page_icon="DO", layout="wide")
st.title("Data Observability Monitor")
st.caption("Les 5 piliers : fraîcheur · volume · schéma · distribution · lignage")

if not DB_PATH.exists():
    st.warning("Aucune métrique. Exécutez d'abord observability.py pour clean puis corrupted.")
    st.stop()

with sqlite3.connect(DB_PATH) as conn:
    metrics = pd.read_sql_query("SELECT * FROM observability_metrics ORDER BY timestamp", conn)

if metrics.empty:
    st.warning("Aucune métrique disponible.")
    st.stop()

metrics["run"] = metrics["batch"] + " · " + pd.to_datetime(metrics["timestamp"]).dt.strftime("%H:%M:%S")
latest = metrics.iloc[-1]

status = str(latest["status"])
if status == "objectif":
    st.success("STATUT : OBJECTIF — toutes les métriques sont dans la cible")
elif status == "alerte":
    st.warning("STATUT : ALERTE — au moins un indicateur dérive")
else:
    st.error("STATUT : CRITIQUE — le schéma est cassé")


def badge(ok: bool) -> str:
    return "OK" if ok else "ALERTE"


st.subheader("Les 5 piliers (dernier lot)")
p1, p2, p3, p4, p5 = st.columns(5)
fresh = latest["freshness_hours"]
p1.metric("Fraîcheur", f"{fresh:.0f} h de retard" if pd.notna(fresh) else "n/a",
          badge(latest["freshness_status"] == "objectif"), delta_color="off")
p2.metric("Volume", f"{int(latest['row_count']):,} lignes",
          badge(latest["volume_status"] == "objectif"), delta_color="off")
p3.metric("Schéma", "conforme" if bool(latest["schema_ok"]) else f"manque : {latest['missing_columns']}",
          badge(bool(latest["schema_ok"])), delta_color="off")
drift = latest["price_drift_pct"]
p4.metric("Distribution", f"prix moyen {drift:+.1f}%" if pd.notna(drift) else "n/a",
          badge(latest["distribution_status"] == "objectif"), delta_color="off")
p5.metric("Lignage", str(latest["source_file"]), "source → métriques → SQLite", delta_color="off")

st.subheader("Profilage des colonnes")
c1, c2 = st.columns(2)
c1.metric("Complétude", f"{latest['completeness_pct']:.2f}%")
c2.metric("Doublons order_id", f"{int(latest['duplicate_order_ids']):,}")

left, right = st.columns(2)
with left:
    st.subheader("Volume des lots")
    fig = px.bar(metrics, x="run", y="row_count", text="row_count", color="volume_status",
                 color_discrete_map={"objectif": "#2e8b57", "alerte": "#d9822b"})
    fig.update_layout(yaxis_title="Nombre de lignes", xaxis_title="")
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Prix moyen par lot")
    fig = px.bar(metrics, x="run", y="avg_unit_price", text="avg_unit_price", color="distribution_status",
                 color_discrete_map={"objectif": "#2e8b57", "alerte": "#d9822b"})
    fig.update_layout(yaxis_title="Prix unitaire moyen", xaxis_title="")
    st.plotly_chart(fig, width="stretch")

st.subheader("Historique des métriques")
display = metrics[["timestamp", "batch", "row_count", "freshness_hours", "price_drift_pct",
                   "schema_ok", "completeness_pct", "duplicate_order_ids", "status"]].copy()
display.columns = ["Timestamp", "Lot", "Lignes", "Retard (h)", "Dérive prix (%)",
                   "Schéma OK", "Complétude (%)", "Doublons", "Statut"]
st.dataframe(display, width="stretch", hide_index=True)
