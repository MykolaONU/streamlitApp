import re
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
from io import BytesIO
from function import addColumns

# --- Типові позиції зрізів ---
default_column_slices = {
    'ymd': (0, 9),
    'to': (9, 15),
    'tm': (15, 20),
    'te': (20, 26),
    'xray/opt': (26, 35),
    'L': (35, 42),
    'coord': (42, 53),
    'AR': (53, 59),
    'radio': (59, 65),
    'mhr': (65, 72),
    'dynamic': (72, 77),
    'sweep': (77, 81),
    'CME': (81, 100),
    'xray-hard': (100, 124),
    'protons': (124, None)
}

# --- Ініціалізація session state ---
if "column_slices" not in st.session_state:
    st.session_state.column_slices = default_column_slices.copy()
if "selected_column" not in st.session_state:
    st.session_state.selected_column = list(default_column_slices.keys())[0]

# --- Допоміжна функція: парсинг PDF у DataFrame ---
def parse_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    pattern = re.compile(r"^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})\s+")
    data_list = []

    for page in reader.pages:
        text = page.extract_text()
        for line in text.splitlines():
            if pattern.match(line):
                row = []
                for col, (start, end) in st.session_state.column_slices.items():
                    value = line[start:end].strip() if end else line[start:].strip()
                    row.append(value)
                data_list.append(row)
    df = pd.DataFrame(data_list, columns=list(st.session_state.column_slices.keys()))
    return addColumns(df)

# --- Бокова панель: редагування колонок ---
def show_column_editor():
    st.sidebar.header("Налаштування колонок")
    columns = list(st.session_state.column_slices.keys())
    selected_column = st.sidebar.selectbox("Оберіть колонку", columns, index=columns.index(st.session_state.selected_column))
    st.session_state.selected_column = selected_column

    col_index = columns.index(selected_column)
    current_start, current_end = st.session_state.column_slices[selected_column]

    # Зберігаємо попередні значення для порівняння
    prev_start = st.session_state.get(f"{selected_column}_prev_start", current_start)
    prev_end = st.session_state.get(f"{selected_column}_prev_end", current_end if current_end else 0)

    # Поля введення
    new_start = st.sidebar.number_input("Зсув зліва", value=current_start, key=f"{selected_column}_start_input")
    new_end = st.sidebar.number_input("Зсув справа (0 = до кінця)", value=current_end if current_end else 0, key=f"{selected_column}_end_input")

    updated_end = int(new_end) if new_end != 0 else None

    # Оновлюємо поточну колонку
    st.session_state.column_slices[selected_column] = (int(new_start), updated_end)

    # Оновлюємо сусідні колонки
    if col_index + 1 < len(columns):
        next_col = columns[col_index + 1]
        _, next_end = st.session_state.column_slices[next_col]
        st.session_state.column_slices[next_col] = (updated_end if updated_end is not None else new_start, next_end)

    if col_index - 1 >= 0:
        prev_col = columns[col_index - 1]
        prev_start_val, _ = st.session_state.column_slices[prev_col]
        st.session_state.column_slices[prev_col] = (prev_start_val, int(new_start))

    # Зберігаємо попередні значення
    st.session_state[f"{selected_column}_prev_start"] = int(new_start)
    st.session_state[f"{selected_column}_prev_end"] = int(new_end)

    # Якщо є зміни — перезапуск
    if int(new_start) != prev_start or int(new_end) != prev_end:
        st.rerun()

    if st.sidebar.button("🔄 Скинути всі зрізи"):
        st.session_state.column_slices = default_column_slices.copy()
        for col in columns:
            st.session_state.pop(f"{col}_prev_start", None)
            st.session_state.pop(f"{col}_prev_end", None)
        st.rerun()

# --- Основний інтерфейс ---
st.title("Обробка PDF з даними")
uploaded_file = st.file_uploader("Завантажте PDF-файл", type="pdf")

if uploaded_file:
    df = parse_pdf(uploaded_file)

    if st.toggle("⚙️ Показати налаштування зрізів", key="show_editor_toggle"):
        show_column_editor()
    st.success("Попередній перегляд оброблених даних:")
    st.dataframe(df)

    st.session_state.df = df
    st.markdown("---")

    def to_excel_bytes(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button(
        label="📥 Завантажити Excel",
        data=to_excel_bytes(df),
        file_name="результат_обробки.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
