import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import io


# ==========================
# Генерация синтетических данных
# ==========================
@st.cache_data
def generate_data(n_fact_days=60, n_forecast_days=30):
    products = ["Candy A", "Candy B", "Candy C"]
    regions = ["north", "south", "east", "west"]

    today = datetime.today().date()
    fact_dates = pd.date_range(today - timedelta(days=n_fact_days), periods=n_fact_days)
    forecast_dates = pd.date_range(today + timedelta(days=1), periods=n_forecast_days)

    rows = []
    for product in products:
        for region in regions:
            # Фактические данные
            for d in fact_dates:
                y = np.random.randint(80, 150)
                yhat = y + np.random.randint(-5, 5)
                rows.append([d, product, region, y, yhat, yhat - 10, yhat + 10])

            # Прогнозные данные (факта нет)
            for d in forecast_dates:
                yhat = np.random.randint(90, 140)
                rows.append([d, product, region, None, yhat, yhat - 15, yhat + 15])

    df = pd.DataFrame(
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
    return df


@st.cache_data
def generate_model_metrics():
    rows = []
    for product in ["Candy A", "Candy B", "Candy C"]:
        for region in ["north", "south", "east", "west"]:
            rows.append(
                [
                    "prophet",
                    np.round(np.random.uniform(5, 10), 2),  # mae
                    np.round(np.random.uniform(7, 12), 2),  # rmse
                    np.round(np.random.uniform(1, 3), 2),  # wape
                    np.round(np.random.uniform(15, 30), 2),  # summ_error_3month
                    product,
                    region,
                ]
            )
    df = pd.DataFrame(
        rows,
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
    return df


# ==========================
# Настройки страницы
# ==========================
st.set_page_config(
    page_title="Amiri Forecasting Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Amiri Forecasting Dashboard")

# ==========================
# Данные
# ==========================
forecast_df = generate_data()
metrics_df = generate_model_metrics()

# ==========================
# Фильтры (sidebar)
# ==========================
st.sidebar.header("Фильтры")

product = st.sidebar.selectbox("Выберите продукт", forecast_df["product_name"].unique())
region = st.sidebar.selectbox("Выберите регион", forecast_df["region"].unique())
horizon = st.sidebar.slider("Горизонт прогноза (дней)", 1, 90, 30)

filtered_df = forecast_df[
    (forecast_df["product_name"] == product) & (forecast_df["region"] == region)
].copy()

# Ограничиваем горизонтом
filtered_df = filtered_df.sort_values("date").tail(horizon)

# ==========================
# Вкладки
# ==========================
tab1, tab2 = st.tabs(["📈 Прогноз vs Факт", "📉 Метрики модели"])

with tab1:
    st.subheader(f"Прогноз vs Факт для {product} ({region})")

    if filtered_df.empty:
        st.warning("⚠️ Нет данных для выбранных фильтров.")
    else:
        today = datetime.today().date()

        # Стили осей (чёткие подписи в тёмной теме)
        x_axis = alt.X(
            "date:T",
            title="📅 Дата",
            axis=alt.Axis(
                labelFontSize=12,
                titleFontSize=16,
                titleColor="white",
                labelColor="white",
            ),
        )
        y_axis = alt.Y(
            "y:Q",
            title="📦 Продажи",
            axis=alt.Axis(
                labelFontSize=12,
                titleFontSize=16,
                titleColor="white",
                labelColor="white",
            ),
        )

        # Факт
        line_fact = (
            alt.Chart(filtered_df.dropna(subset=["y"]))
            .mark_line(color="steelblue")
            .encode(x=x_axis, y=y_axis, tooltip=["date", "y"])
        )

        # Прогноз
        line_forecast = (
            alt.Chart(filtered_df)
            .mark_line(color="orange", strokeDash=[5, 5])
            .encode(
                x="date:T",
                y=alt.Y("yhat:Q", title="📦 Продажи"),
                tooltip=["date", "yhat"],
            )
        )

        # Интервал прогноза
        band = (
            alt.Chart(filtered_df)
            .mark_area(opacity=0.2, color="orange")
            .encode(x="date:T", y="yhat_lower:Q", y2="yhat_upper:Q")
        )

        # Вертикальная линия «сегодня»
        today_rule = (
            alt.Chart(pd.DataFrame({"date": [today]}))
            .mark_rule(strokeDash=[2, 2], color="red")
            .encode(x="date:T")
        )

        # Комбинируем
        chart = (line_fact + line_forecast + band + today_rule).properties(
            width=900, height=400
        )

        st.altair_chart(chart, use_container_width=True)

        # Таблица
        st.subheader("Таблица прогнозов")
        st.dataframe(filtered_df, use_container_width=True)

        # Скачивание CSV
        st.download_button(
            "⬇️ Скачать CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"forecast_{product}_{region}.csv",
            mime="text/csv",
        )

        # Скачивание Excel
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Forecast")
        towrite.seek(0)

        st.download_button(
            "⬇️ Скачать Excel",
            data=towrite,
            file_name=f"forecast_{product}_{region}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with tab2:
    st.subheader("Метрики модели")

    metrics_filtered = metrics_df[
        (metrics_df["product_name"] == product) & (metrics_df["region"] == region)
    ]

    if metrics_filtered.empty:
        st.warning("⚠️ Нет метрик для выбранной комбинации.")
    else:
        st.dataframe(metrics_filtered, use_container_width=True)
