import streamlit as st
import pandas as pd
import plotly.express as px
from function import addColumns

st.title("📊 Графіки сонячних спалахів")

# Завжди пропонуємо завантажити новий файл
uploaded_file = st.file_uploader("Завантажте файл Excel або CSV (повторне завантаження перезапише поточні дані)", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file, dtype=str)
        else:
            df = pd.read_csv(uploaded_file, dtype=str)
        st.session_state.df = df
        st.success("Файл успішно завантажено та оброблено.")
    except Exception as e:
        st.error(f"Помилка при завантаженні файлу: {e}")
        st.stop()

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

# Перемикач групування
group_by = st.radio(
    "Групувати за:",
    options=["Дні", "Місяці", "Роки"],
    horizontal=True
)

# Створення стовпця групування
if group_by == "Дні":
    filtered_df["group"] = filtered_df["date"].dt.date
elif group_by == "Місяці":
    filtered_df["group"] = filtered_df["date"].dt.to_period("M").dt.to_timestamp()
elif group_by == "Роки":
    filtered_df["group"] = filtered_df["date"].dt.to_period("Y").dt.to_timestamp()

# Стовпчикова діаграма кількості спалахів
count_by_group = (
    filtered_df.groupby("group")
    .size()
    .reset_index(name="Кількість спалахів")
)

fig_bar = px.bar(count_by_group, x="group", y="Кількість спалахів",
                 title=f"Частота сонячних спалахів за {group_by.lower()}")
st.plotly_chart(fig_bar, use_container_width=True)

# Обробка числових стовпців
numeric_cols = ["lat", "lon", "brightness", "importance", "peak_flux"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Точкова діаграма з екватором
fig_scatter = px.scatter(
    filtered_df,
    x="group",
    y="lat",
    color="x_ray_class",
    size="peak_flux",
    hover_data=["brightness", "importance"],
    labels={"group": "Дата", "lat": "Широта"},
    title="Розподіл сонячних спалахів за широтою у часі",
    height=600
)
fig_scatter.add_hline(
    y=0,
    line_dash="dash",
    line_color="gray",
    annotation_text="Екватор",
    annotation_position="top left"
)
fig_scatter.update_yaxes(title="Широта (°)", range=[-90, 90])
st.plotly_chart(fig_scatter, use_container_width=True)
