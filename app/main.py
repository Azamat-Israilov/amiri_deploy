import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import altair as alt

st.set_page_config(page_title="Amiri Forecasting UI", layout="wide")

# 🔹 Заголовок
st.markdown(
    """
    <h1 style='text-align: center; color: #FF4B4B; font-size: 48px;'>
        🍬 Amiri Forecasting UI
    </h1>
    <p style='text-align: center; color: gray; font-size:18px;'>
        Анализ прогноза vs факта по спросу на конфеты
    </p>
    """,
    unsafe_allow_html=True,
)

# --- Фильтры ---
st.sidebar.header("📅 Фильтр дат")
start_date = st.sidebar.date_input("Начальная дата")
end_date = st.sidebar.date_input("Конечная дата")

# --- Генерация данных ---
if st.sidebar.button("🔮 Сгенерировать прогноз (синтетика)"):
    dates = pd.date_range(start_date, end_date)
    forecast = np.random.randint(100, 200, size=len(dates))
    actual = forecast + np.random.randint(-10, 10, size=len(dates))

    df = pd.DataFrame({"date": dates, "forecast": forecast, "actual": actual})

    # сохраняем данные в session_state
    st.session_state["forecast_data"] = df

# --- Проверка: есть ли данные ---
if "forecast_data" in st.session_state:
    df = st.session_state["forecast_data"]

    # --- График ---
    st.subheader("📊 Прогноз vs Факт")
    df_melted = df.melt("date", var_name="Показатель", value_name="Значение")

    chart = (
        alt.Chart(df_melted)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Дата"),
            y=alt.Y("Значение:Q", title="Количество"),
            color=alt.Color("Показатель:N", legend=alt.Legend(title="Линии")),
            tooltip=["date:T", "Показатель:N", "Значение:Q"],
        )
        .properties(width=900, height=400)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # --- Таблица ---
    st.subheader("📋 Таблица прогнозов")
    table_style = st.radio(
        "Выберите стиль таблицы:",
        ("Обычная", "С градиентной подсветкой"),
        horizontal=True,
    )

    if table_style == "Обычная":
        st.dataframe(df, use_container_width=True)
    else:
        styled_df = df.style.background_gradient(cmap="YlGnBu")
        st.dataframe(styled_df, use_container_width=True)

    # --- Скачать CSV ---
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Скачать CSV", data=csv, file_name="forecast.csv", mime="text/csv"
    )

    # --- Скачать Excel ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Forecast")
    st.download_button(
        "📊 Скачать Excel",
        data=output.getvalue(),
        file_name="forecast.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

else:
    st.info("👈 Выберите даты и нажмите кнопку в боковой панели для генерации прогноза")
