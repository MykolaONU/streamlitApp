import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO


from sklearn.preprocessing import StandardScaler
from sklearn.cluster import (
    KMeans,
    DBSCAN,
    AgglomerativeClustering,
    Birch,
)
from sklearn.metrics import silhouette_score

import plotly.express as px

from function import addColumns  # ➡️ утиліти з Visualize
import os

# ----------------------------------------------------------------------------
# ⚙️ Конфігурація сторінки
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Кластерний аналіз", layout="wide")

st.title("🧩 Кластерний аналіз сонячних спалахів")

# ----------------------------------------------------------------------------
# 1️⃣ Завантаження даних
# ----------------------------------------------------------------------------

def load_dataframe(src):
    """Читання CSV / Excel чи UploadedFile у DataFrame (dtype=str)."""
    if isinstance(src, str):
        return pd.read_csv(src, dtype=str)
    ext = os.path.splitext(src.name)[-1].lower()
    if ext == ".xlsx":
        return pd.read_excel(src, dtype=str)
    return pd.read_csv(src, dtype=str)

uploaded_file = st.file_uploader(
    "Завантажте файл Excel або CSV (повторне завантаження перезапише поточні дані)",
    type=["xlsx", "csv"],
)

DEFAULT_FILE = "data/extracted_data.csv"

if "df" not in st.session_state:
    if uploaded_file:
        st.session_state.df = load_dataframe(uploaded_file)
    elif os.path.exists(DEFAULT_FILE):
        st.session_state.df = load_dataframe(DEFAULT_FILE)
    else:
        st.warning("Спочатку завантажте вхідний файл.")
        st.stop()

if uploaded_file:
    st.session_state.df = load_dataframe(uploaded_file)

df_raw = st.session_state.df.copy()

df = addColumns(df_raw)

# ----------------------------------------------------------------------------
# 2️⃣ Попередня обробка
# ----------------------------------------------------------------------------
req_cols = [
    "x_ray_class",
    "peak_flux",
    "lat",
    "lon",
    "duration_minutes",
    "L",
    "date",
]
missing = [c for c in req_cols if c not in df.columns]
if missing:
    st.error("Відсутні стовпці: " + ", ".join(missing))
    st.stop()

# Фільтруємо на M та X класи (топові спалахи)
df = df[df["x_ray_class"].isin(["M", "X"])].copy()

# Типи даних
num_cols = ["peak_flux", "lat", "lon", "duration_minutes", "L"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
class_map = {"A": 0, "B": 1, "C": 2, "M": 3, "X": 4}
df["x_ray_class_num"] = df["x_ray_class"].map(class_map)

# ----------------------------------------------------------------------------
# 3️⃣ Sidebar – параметри кластеризації
# ----------------------------------------------------------------------------
feature_choices = {
    "x_ray_class_num": "Клас X-ray (num)",
    "peak_flux": "Peak flux",
    "lat": "Широта",
    "lon": "Довгота",
    "duration_minutes": "Тривалість (хв)",
    "L": "L",
}

with st.sidebar:
    st.header("⚙️ Параметри")
    selected_features = st.multiselect(
        "Ознаки", list(feature_choices.values()),
        default=[feature_choices["x_ray_class_num"], feature_choices["peak_flux"], feature_choices["L"]],
    )
    feature_cols = [k for k, v in feature_choices.items() if v in selected_features]

    algo = st.selectbox(
        "Алгоритм",
        (
            "KMeans",
            "DBSCAN",
            # "Agglomerative",
            "Birch",
        ),
    )

    # Динамічні параметри
    if algo == "KMeans":
        k = st.number_input("K (кластерів)", 2, 15, 3, 1)
    # elif algo == "Agglomerative":
    #     k = st.number_input("Кластерів", 2, 15, 3, 1)
    #     linkage = st.selectbox("Linkage", ("ward", "complete", "average", "single"))
    elif algo == "Birch":
        k = st.number_input("Кластерів", 2, 15, 3, 1)
        threshold = st.slider("threshold", 0.1, 3.0, 0.5, 0.1)
    else:  # DBSCAN
        eps = st.slider("eps", 0.1, 3.0, 1.2, 0.1)
        min_samples = st.number_input("min_samples", 3, 20, 5, 1)

    run_btn = st.button("🚀 Запустити")

if not run_btn:
    st.info("Натисніть кнопку \"Запустити\" у боковій панелі.")
    st.stop()

# ----------------------------------------------------------------------------
# 4️⃣ Матриця ознак
# ----------------------------------------------------------------------------
df_clu = df.dropna(subset=feature_cols).copy()
if df_clu.empty:
    st.error("Недостатньо даних після видалення пропусків.")
    st.stop()

X = df_clu[feature_cols]
X_scaled = StandardScaler().fit_transform(X)

# ----------------------------------------------------------------------------
# 5️⃣ Кластеризація
# ----------------------------------------------------------------------------
if algo == "KMeans":
    model = KMeans(n_clusters=int(k), random_state=42, n_init="auto")
    labels = model.fit_predict(X_scaled)
elif algo == "DBSCAN":
    model = DBSCAN(eps=float(eps), min_samples=int(min_samples))
    labels = model.fit_predict(X_scaled)
# elif algo == "Agglomerative":
#     model = AgglomerativeClustering(n_clusters=int(k), linkage=linkage)
#     labels = model.fit_predict(X_scaled)
else:  # Birch
    model = Birch(n_clusters=int(k), threshold=threshold)
    labels = model.fit_predict(X_scaled)

# Silhouette (коли доречно)
unique_lbls = set(labels)
num_clusters = len(unique_lbls) - (1 if -1 in unique_lbls else 0)
if num_clusters > 1:
    sil = silhouette_score(X_scaled, labels)
    st.sidebar.success(f"Silhouette: {sil:.3f}")
else:
    st.sidebar.warning("Silhouette: N/A (≤1 кластер)")

df_clu["cluster"] = labels.astype(str)

# ----------------------------------------------------------------------------
# 6️⃣ Візуалізація результатів
# ----------------------------------------------------------------------------

st.subheader("📊")
fig = px.scatter(
    df_clu,
    x='date',
    y='lat',
    color="cluster",
    hover_data=["date", "x_ray_class", "peak_flux", "duration_minutes", "L"],
    title=f"{algo}: {feature_cols[0]} vs {feature_cols[1]}",
)
fig.add_hline(
    y=0,
    line_dash="dash",
    line_color="gray",
    annotation_text="Екватор",
    annotation_position="top left"
)
fig.update_layout(height=500)
fig.update_traces(marker=dict(line=dict(width=1)))
fig.update_yaxes(title="Широта (°)", range=[-90, 90])
st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# 7️⃣ Підсумкова статистика
# ----------------------------------------------------------------------------
st.subheader("📑 Статистика по кластерах")
summary = df_clu.groupby("cluster")[feature_cols].agg(["mean", "std", "count"])
st.markdown('Клас спалаху - "A": 0, "B": 1, "C": 2, "M": 3, "X": 4')
st.dataframe(summary)
score = silhouette_score(X_scaled, df_clu["cluster"])
st.markdown(f"Silhouette Score: {score:.3f}")

# ----------------------------------------------------------------------------
# 8️⃣ Завантаження результатів
# ----------------------------------------------------------------------------
@st.cache_data
def df_to_excel(df_: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_.to_excel(writer, index=False)
    return output.getvalue()

st.download_button(
    label="💾 Завантажити Excel",
    data=df_to_excel(df_clu),
    file_name="clusters.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)