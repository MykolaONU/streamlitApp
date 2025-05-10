import streamlit as st
from io import BytesIO
import pandas as pd
from function import process_pdf  # Или вставь саму функцию сюда, если без модуля

st.title("Загрузка PDF и экспорт в Excel")

uploaded_file = st.file_uploader("Загрузите PDF-файл", type=["pdf"])

if uploaded_file:
    st.info("Обработка файла...")
    df = process_pdf(uploaded_file)

    st.success("Файл обработан. Предварительный просмотр:")
    st.dataframe(df)

    # Скачивание Excel
    def to_excel_bytes(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button(
        label="Скачать Excel",
        data=to_excel_bytes(df),
        file_name="результат_обработки.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
