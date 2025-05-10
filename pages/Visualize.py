import streamlit as st
import pandas as pd
import plotly.express as px

st.title("📊 Графики по солнечным вспышкам")

# Проверяем наличие df
if "df" not in st.session_state:
    st.warning("Сначала загрузите и обработайте PDF на главной странице, либо загрузите файл Excel/CSV ниже.")

    uploaded_file = st.file_uploader("Загрузите файл Excel или CSV", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            st.session_state.df = df
            st.success("Файл успешно загружен.")
        except Exception as e:
            st.error(f"Ошибка при загрузке файла: {e}")
            st.stop()
    else:
        st.stop()

df = st.session_state.df

# Обработка даты
if "date" in df.columns:
    try:
        df["date"] = pd.to_datetime(df["date"])
    except:
        st.error("Не удалось преобразовать колонку 'date' в формат даты.")
        st.stop()
else:
    st.error("Колонка 'date' не найдена.")
    st.stop()

# Слайсер по дате
min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.slider(
    "Выберите диапазон дат",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD"
)

# Фильтрация по диапазону
filtered_df = df[
    (df["date"] >= pd.to_datetime(date_range[0])) &
    (df["date"] <= pd.to_datetime(date_range[1]))
]

# Переключатель группировки
group_by = st.radio(
    "Группировать по:",
    options=["Дни", "Месяцы", "Годы"],
    horizontal=True
)

# Создание столбца группировки
if group_by == "Дни":
    filtered_df["group"] = filtered_df["date"].dt.date
elif group_by == "Месяцы":
    filtered_df["group"] = filtered_df["date"].dt.to_period("M").dt.to_timestamp()
elif group_by == "Годы":
    filtered_df["group"] = filtered_df["date"].dt.to_period("Y").dt.to_timestamp()

# Группировка и визуализация
count_by_group = (
    filtered_df.groupby("group")
    .size()
    .reset_index(name="Количество вспышек")
)

fig = px.bar(count_by_group, x="group", y="Количество вспышек",
             title=f"Частота солнечных вспышек по {group_by.lower()}")
st.plotly_chart(fig, use_container_width=True)


numeric_cols = ["lat", "lon", "brightness", "importance", "peak_flux"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

fig = px.scatter(
    filtered_df,
    x="group",
    y="lat",
    color="x_ray_class",
    size="peak_flux",
    hover_data=["brightness", "importance"],
    labels={"group": "Дата", "lat": "Широта"},
    title="Распределение солнечных вспышек по широте во времени",
    height=600
)
fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Экватор", annotation_position="top left")

fig.update_yaxes(title="Широта (°)", range=[-90, 90])
st.plotly_chart(fig, use_container_width=True)