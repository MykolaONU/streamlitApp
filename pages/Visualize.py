import streamlit as st
import pandas as pd
import plotly.express as px
from function import addColumns
import os
import numpy as np

xray_class_colors = {
        "A": "#a9a9a9",  # Сірий
        "B": "#66c2a5",  # Зелено-бірюзовий
        "C": "#fc8d62",  # Помаранчево-червоний
        "M": "#8da0cb",  # Синій
        "X": "#e78ac3",  # Рожевий
    }

common_params = dict(
            color="x_ray_class",
            color_discrete_map=xray_class_colors,
            category_orders={"x_ray_class": list(xray_class_colors.keys())},
            # size="peak_flux",
            opacity=0.7,
            labels={"lat": "Широта (°)", "date": "Дата", "group": "Дата"},
        )


st.title("📊 Графіки сонячних спалахів")

# Завжди пропонуємо завантажити новий файл
uploaded_file = st.file_uploader("Завантажте файл Excel або CSV (повторне завантаження перезапише поточні дані)", type=["xlsx", "csv"])

# Завантаження дефолтного файлу, якщо користувач не завантажив свій
DEFAULT_FILE_PATH = "data/extracted_data.csv"
if "df" not in st.session_state and os.path.exists(DEFAULT_FILE_PATH):
    try:
        df = pd.read_csv(DEFAULT_FILE_PATH, dtype=str)
        st.session_state.df = df
    except Exception as e:
        st.warning(f"Не вдалося завантажити файл за замовчуванням: {e}")

# Перевірка наявності даних
if "df" not in st.session_state:
    st.warning("Спочатку завантажте та обробіть PDF на головній сторінці або Excel/CSV-файл вище.")
    st.stop()

df = st.session_state.df
df = addColumns(df)

# Обробка дати
if "date" in df.columns:
    try:
        df["date"] = pd.to_datetime(df["date"])
    except:
        st.error("Не вдалося перетворити стовпець 'date' у формат дати.")
        st.stop()
else:
    st.error("Стовпець 'date' не знайдено.")
    st.stop()

# Слайдер для вибору діапазону дат
min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.slider(
    "Оберіть діапазон дат",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Фільтрація за обраним діапазоном
filtered_df = df[
    (df["date"] >= pd.to_datetime(date_range[0])) &
    (df["date"] <= pd.to_datetime(date_range[1]))
]

# Стовпчикова діаграма кількості спалахів
count_by_group = (
    filtered_df.groupby("date")
    .size()
    .reset_index(name="Кількість спалахів")
)

fig_bar = px.bar(count_by_group, x="date", y="Кількість спалахів",
                 title=f"Частота сонячних спалахів")
st.plotly_chart(fig_bar, use_container_width=True)

# Обробка числових стовпців
numeric_cols = ["lat", "lon", "peak_flux"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Точкова діаграма з екватором
fig_scatter = px.scatter(
    filtered_df,
    x="date",
    y="lat",
    hover_data=["brightness", "importance"],
    # labels={"group": "Дата", "lat": "Широта"},
    title="Розподіл сонячних спалахів за широтою у часі",
    **common_params
)
fig_scatter.add_hline(
    y=0,
    line_dash="dash",
    line_color="gray",
    annotation_text="Екватор",
    annotation_position="top left"
)
fig_scatter.update_yaxes(title="Широта (°)", range=[-90, 90])
fig_scatter.update_traces(marker=dict(line=dict(width=1)))
st.plotly_chart(fig_scatter, use_container_width=True)

# Графік 1: Усі спалахи з окремими лініями тренду для кожної півкулі
df_clean = df[["date", "lat", "x_ray_class", "lat_hemisphere", "brightness", "importance"]].copy()
df_clean = df_clean.dropna(subset=["date", "lat", "lat_hemisphere"])

fig_all = px.scatter(
    df_clean,
    x="date",
    y="lat",
    hover_data=["date", "brightness", "importance"],
    title=f"Широти всіх спалахів",
    **common_params
)
fig_all.update_layout(height=500)
fig_all.update_yaxes(title="Широта (°)", range=[-90, 90])
fig_all.update_traces(marker=dict(line=dict(width=1)))

# Додаємо лінії тренду для кожної півкулі з формулами
for hemisphere, group in df_clean.groupby("lat_hemisphere"):
    group = group.sort_values("date")
    if len(group) < 2:
        continue

    # Перетворюємо дату у числовий формат для поліноміальної апроксимації
    x_numeric = pd.to_numeric(group["date"])
    y = group["lat"]
    coef = np.polyfit(x_numeric, y, 1)
    trend_fn = np.poly1d(coef)
    # Побудова лінії тренду
    x_range = np.linspace(x_numeric.min(), x_numeric.max(), 100)
    y_trend = trend_fn(x_range)

    # Рівняння у форматі: y = a·x + b
    a, b = coef
    equation = f"y = {a:.2e}·x + {b:.2f}"

    # Додаємо лінію на графік
    fig_all.add_scatter(
        x=pd.to_datetime(x_range),
        y=y_trend,
        mode="lines",
        name=f"Тренд ({hemisphere}): {equation}",
        line=dict(width=2, dash="dot"),
        opacity = 1
    )
fig_all.update_yaxes(title="Широта (°)", range=[-90, 90])
fig_all.update_traces(marker=dict(line=dict(width=1)))
st.plotly_chart(fig_all, use_container_width=True)


# --- Візуалізація по кожному циклу ---
if "cycle" in df.columns:
    st.header("🔁 Графіки по кожному циклу")

    df["cycle"] = df["cycle"].astype(str).str.strip()
    cycles = df["cycle"].dropna().unique()

    for cycle in sorted(cycles):
        st.subheader(f"☀️ Цикл {cycle}")
        df_cycle = df[df["cycle"] == cycle]

        # --- Загальна статистика по циклу ---
        total_count = len(df_cycle)
        cme_count = len(df_cycle[(df_cycle['CME'].str.strip().str.len()>4) & (~df_cycle["CME"].isna())])
        proton_count = len(df_cycle[(~df_cycle["protons"].isna()) & (df_cycle['protons'].str.strip().str.len()>4)])
        cme_percent = (cme_count / total_count * 100) if total_count > 0 else 0
        proton_percent = (proton_count / total_count * 100) if total_count > 0 else 0

        st.markdown(
            f"""
            **📊 Статистика по циклу {cycle}:**
            - Загальна кількість спалахів: **{total_count}**
            - З CME: **{cme_count}** ({cme_percent:.1f}%)
            - Протонних: **{proton_count}** ({proton_percent:.1f}%)
            """
        )

        # Графік 1: Усі спалахи
        fig_all = px.scatter(
            df_cycle,
            x="date",
            y="lat",
            hover_data=["date", "brightness", "importance"],
            title=f"Широти всіх спалахів у циклі {cycle}",
            **common_params
        )
        fig_all.update_layout(height=500)
        fig_all.update_traces(marker=dict(line=dict(width=1)))
        fig_all.update_yaxes(title="Широта (°)", range=[-90, 90])
        st.plotly_chart(fig_all, use_container_width=True)

        # Графік 2: Лише X та M класи
        df_class_xm = df_cycle[df_cycle["x_ray_class"].isin(["X", "M"])]
        if not df_class_xm.empty:
            fig_xm = px.scatter(
                df_class_xm,
                x="date",
                y="lat",
                hover_data=["brightness", "importance"],
                title=f"Широти спалахів класів X і M у циклі {cycle}",
                **common_params
            )
            fig_xm.update_layout(height=500)
            fig_xm.update_traces(marker=dict(line=dict(width=1)))
            fig_xm.update_yaxes(title="Широта (°)", range=[-90, 90])
            st.plotly_chart(fig_xm, use_container_width=True)

        # Графік 3: Лише ті, що з CME
        df_cme = df_cycle[df_cycle['isCMEFlare'] == 1]
        if not df_cme.empty:
            fig_cme = px.scatter(
                df_cme,
                x="date",
                y="lat",
                hover_data=["brightness", "importance", "CME"],
                title=f"Широти спалахів з CME у циклі {cycle}",
                **common_params
            )
            fig_cme.update_layout(height=500)
            fig_cme.update_traces(marker=dict(line=dict(width=1)))
            fig_cme.update_yaxes(title="Широта (°)", range=[-90, 90])
            st.plotly_chart(fig_cme, use_container_width=True)

        # Графік 4: Протонні спалахи
        df_protons = df_cycle[df_cycle['isProtonFlare'] == 1]
        if not df_protons.empty:
            fig_protons = px.scatter(
                df_protons,
                x="date",
                y="lat",
                hover_data=["brightness", "importance", "protons"],
                title=f"Широти протонних спалахів у циклі {cycle}",
                **common_params
            )
            fig_protons.update_layout(height=500)
            fig_protons.update_traces(marker=dict(line=dict(width=1)))
            fig_protons.update_yaxes(title="Широта (°)", range=[-90, 90])
            st.plotly_chart(fig_protons, use_container_width=True)

        # Графік 1: Усі спалахи з окремими лініями тренду для кожної півкулі
        df_cycle_clean = df_cycle[["date", "lat", "x_ray_class", "lat_hemisphere", "brightness", "importance"]].copy()
        df_cycle_clean = df_cycle_clean.dropna(subset=["date", "lat", "lat_hemisphere"])

        fig_all = px.scatter(
            df_cycle_clean,
            x="date",
            y="lat",
            hover_data=["date", "brightness", "importance"],
            title=f"Широти всіх спалахів у циклі {cycle}",
            **common_params
        )
        fig_all.update_layout(height=500)
        fig_all.update_yaxes(title="Широта (°)", range=[-90, 90])
        fig_all.update_traces(marker=dict(line=dict(width=1)))

        # Додаємо лінії тренду для кожної півкулі з формулами
        for hemisphere, group in df_cycle_clean.groupby("lat_hemisphere"):
            group = group.sort_values("date")
            if len(group) < 2:
                continue

            # Перетворюємо дату у числовий формат для поліноміальної апроксимації
            x_numeric = pd.to_numeric(group["date"])
            y = group["lat"]
            coef = np.polyfit(x_numeric, y, 1)
            trend_fn = np.poly1d(coef)
            # Побудова лінії тренду
            x_range = np.linspace(x_numeric.min(), x_numeric.max(), 100)
            y_trend = trend_fn(x_range)

            # Рівняння у форматі: y = a·x + b
            a, b = coef
            equation = f"y = {a:.2e}·x + {b:.2f}"

            # Додаємо лінію на графік
            fig_all.add_scatter(
                x=pd.to_datetime(x_range),
                y=y_trend,
                mode="lines",
                name=f"Тренд ({hemisphere}): {equation}",
                line=dict(width=2, dash="dot"),
                opacity = 1
            )

        st.plotly_chart(fig_all, use_container_width=True)

