import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
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
        Факт vs Прогноз продаж конфет (синтетические данные)
    </p>
    """,
    unsafe_allow_html=True,
)


# --- Генерация синтетики ---
@st.cache_data
def generate_data(fact_days=60, forecast_days=30):
    np.random.seed(42)
    products = ["Candy A", "Candy B", "Candy C"]
    regions = ["north", "south"]

    start_date = datetime.today() - timedelta(days=fact_days)
    all_dates = pd.date_range(start=start_date, periods=fact_days + forecast_days)

    rows = []
    for product in products:
        for region in regions:
            # факт (60 дней)
            y_fact = np.random.randint(80, 200, size=fact_days)
            yhat_fact = y_fact + np.random.normal(0, 10, size=fact_days)
            yhat_lower_fact = yhat_fact - np.random.randint(5, 15, size=fact_days)
            yhat_upper_fact = yhat_fact + np.random.randint(5, 15, size=fact_days)

            # прогноз (30 дней)
            yhat_future = np.random.randint(100, 220, size=forecast_days)
            yhat_lower_future = yhat_future - np.random.randint(
                5, 15, size=forecast_days
            )
            yhat_upper_future = yhat_future + np.random.randint(
                5, 15, size=forecast_days
            )

            # собираем факт
            for i in range(fact_days):
                rows.append(
                    [
                        all_dates[i],
                        product,
                        region,
                        y_fact[i],
                        yhat_fact[i],
                        yhat_lower_fact[i],
                        yhat_upper_fact[i],
                    ]
                )

            # собираем прогноз (y = NaN, т.к. факта ещё нет)
            for i in range(forecast_days):
                rows.append(
                    [
                        all_dates[fact_days + i],
                        product,
                        region,
                        np.nan,
                        yhat_future[i],
                        yhat_lower_future[i],
                        yhat_upper_future[i],
                    ]
                )

    forecast_df = pd.DataFrame(
        rows,
        columns=[
            "date",
            "product_name",
            "region",
            "y",
            "yhat",
            "yhat_lower",
            "yhat_upper",
        ],
    )

    # метрики модели (рандомные)
    metrics = []
    for product in products:
        for region in regions:
            mae = np.random.uniform(5, 15)
            rmse = mae + np.random.uniform(2, 5)
            wape = np.random.uniform(2, 10)
            summ_error = np.random.uniform(-50, 50)
            metrics.append(["prophet", mae, rmse, wape, summ_error, product, region])

    metrics_df = pd.DataFrame(
        metrics,
        columns=[
            "model_name",
            "mae",
            "rmse",
            "wape",
            "summ_error_3month",
            "product_name",
            "region",
        ],
    )

    return forecast_df, metrics_df


forecast_df, metrics_df = generate_data()

# --- Фильтры ---
st.sidebar.header("🔍 Фильтры")
products = forecast_df["product_name"].unique().tolist()
regions = forecast_df["region"].unique().tolist()

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

# интервал прогноза
band = (
    alt.Chart(df_filtered)
    .mark_area(opacity=0.2, color="orange")
    .encode(x="date:T", y="yhat_lower:Q", y2="yhat_upper:Q")
)

st.altair_chart(band + chart, use_container_width=True)

# --- Таблица данных ---
st.subheader("📋 Таблица прогнозов")
st.dataframe(df_filtered, use_container_width=True)

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

st.dataframe(metrics_filtered, use_container_width=True)
