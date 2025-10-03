import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# --- Настройки страницы ---
st.set_page_config(page_title="Amiri Forecasting UI", layout="wide")

# --- Заголовок ---
st.markdown(
    """
    <h1 style='text-align: center; color: #FF4B4B; font-size: 42px;'>
        🍬 Amiri Forecasting Dashboard
    </h1>
    <p style='text-align: center; color: gray; font-size:18px;'>
        Факт vs Прогноз продаж конфет + Метрики модели
    </p>
    """,
    unsafe_allow_html=True,
)


# --- Загружаем данные ---
@st.cache_data
def load_data():
    forecast_df = pd.read_excel("forecast_data.xlsx")
    metrics_df = pd.read_excel("model_metrics.xlsx")
    return forecast_df, metrics_df


forecast_df, metrics_df = load_data()

# --- Фильтры ---
st.sidebar.header("🔍 Фильтры")
products = forecast_df["product_name"].dropna().unique().tolist()
regions = forecast_df["region"].dropna().unique().tolist()

product = st.sidebar.selectbox("Выберите продукт:", products)
region = st.sidebar.selectbox("Выберите регион:", regions)
days = st.sidebar.slider("Горизонт прогноза (дней)", 1, 90, 30)

# --- Фильтрация данных ---
df_filtered = forecast_df[
    (forecast_df["product_name"] == product) & (forecast_df["region"] == region)
].copy()

df_filtered = df_filtered.sort_values("date")
if len(df_filtered) > days:
    df_filtered = df_filtered.tail(days)

# --- График ---
st.subheader(f"📊 Прогноз vs Факт: {product} ({region})")

df_melted = df_filtered.melt(
    "date", value_vars=["y", "yhat"], var_name="Показатель", value_name="Значение"
)

chart = (
    alt.Chart(df_melted)
    .mark_line(point=True)
    .encode(
        x=alt.X("date:T", title="Дата"),
        y=alt.Y("Значение:Q", title="Продажи"),
        color=alt.Color("Показатель:N", legend=alt.Legend(title="Линии")),
        tooltip=["date:T", "Показатель:N", "Значение:Q"],
    )
    .properties(width=900, height=400)
    .interactive()
)

# Если есть интервалы прогноза, нарисуем "полосу"
if "yhat_lower" in df_filtered.columns and "yhat_upper" in df_filtered.columns:
    band = (
        alt.Chart(df_filtered)
        .mark_area(opacity=0.2, color="orange")
        .encode(x="date:T", y="yhat_lower:Q", y2="yhat_upper:Q")
    )
    chart = band + chart

st.altair_chart(chart, use_container_width=True)

# --- Таблица данных ---
st.subheader("📋 Таблица прогнозов")
styled_df = df_filtered.style.background_gradient(cmap="YlGnBu")
st.dataframe(styled_df, use_container_width=True)

# --- Скачать CSV ---
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Скачать CSV",
    data=csv,
    file_name=f"{product}_{region}_forecast.csv",
    mime="text/csv",
)

# --- Скачать Excel ---
output = BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_filtered.to_excel(writer, index=False, sheet_name="Forecast")
st.download_button(
    "📊 Скачать Excel",
    data=output.getvalue(),
    file_name=f"{product}_{region}_forecast.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# --- Таблица метрик ---
st.subheader("📈 Метрики модели")
metrics_filtered = metrics_df[
    (metrics_df["product_name"] == product) & (metrics_df["region"] == region)
]

if not metrics_filtered.empty:
    st.dataframe(metrics_filtered, use_container_width=True)
else:
    st.info("Для выбранных продукта и региона метрики пока отсутствуют.")
