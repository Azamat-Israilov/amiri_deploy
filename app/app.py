import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import io
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

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

st.title("Amiri Forecasting Dashboard")

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
horizon = st.sidebar.slider("Горизонт прогноза (дней)", 30, 90, 30)

filtered_df = forecast_df[
    (forecast_df["product_name"] == product) & (forecast_df["region"] == region)
].copy()

# Ограничиваем горизонтом
filtered_df = filtered_df.sort_values("date").tail(horizon)

# ==========================
# Вкладки
# ==========================
tab1, tab2 = st.tabs(["Прогноз vs Факт", "Метрики модели"])

with tab1:
    st.subheader(f"Прогноз vs Факт для {product} ({region})")

    if filtered_df.empty:
        st.warning("Нет данных для выбранных фильтров.")
    else:
        today = datetime.today().date()

        # Стили осей (чёткие подписи в тёмной теме)
    # Предполагается, что переменные:
    # filtered_df, product, region — уже определены ранее

        today = datetime.today().date()

        # Создаем фигуру
        fig = go.Figure()

        # Фактические данные
        actual_data = filtered_df.dropna(subset=["y"])
        if not actual_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=actual_data["date"],
                    y=actual_data["y"],
                    mode="lines+markers",
                    name="Факт",
                    line=dict(color="#1f77b4", width=3),
                    marker=dict(size=4),
                    hovertemplate="<b>Дата:</b> %{x}<br><b>Продажи (факт):</b> %{y}<extra></extra>",
                )
            )

        # Прогнозные данные
        forecast_data = filtered_df.dropna(subset=["yhat"])
        if not forecast_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=forecast_data["date"],
                    y=forecast_data["yhat"],
                    mode="lines+markers",
                    name="Прогноз",
                    line=dict(color="#ff7f0e", width=3, dash="dash"),
                    marker=dict(size=4),
                    hovertemplate="<b>Дата:</b> %{x}<br><b>Продажи (прогноз):</b> %{y}<extra></extra>",
                )
            )

            # Доверительный интервал
            ci_data = forecast_data.dropna(subset=["yhat_lower", "yhat_upper"])
            if not ci_data.empty:
                fig.add_trace(
                    go.Scatter(
                        x=ci_data["date"],
                        y=ci_data["yhat_upper"],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=ci_data["date"],
                        y=ci_data["yhat_lower"],
                        mode="lines",
                        line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(255, 127, 14, 0.2)",
                        name="Доверительный интервал",
                        hoverinfo="skip",
                    )
                )

        # Настройки оформления
        fig.update_layout(
            title=f"Прогноз vs Факт для {product} ({region})",
            xaxis_title="Дата",
            yaxis_title="Продажи",
            template="plotly_white",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis=dict(
                title_font=dict(size=16, family="Arial", color="black"),
                showgrid=True,
                gridwidth=1,
                gridcolor="lightgray",
                tickformat="%d %b",
                range=[filtered_df["date"].min(), filtered_df["date"].max()],
                nticks=8,
            ),
            yaxis=dict(
                title_font=dict(size=16, family="Arial", color="black"),
                showgrid=True,
                gridwidth=1,
                gridcolor="lightgray",
            ),
        )

        # Отображение графика
        st.plotly_chart(fig, use_container_width=True)
        # today = datetime.today().date()
        # filtered_df["y"] = filtered_df.apply(
        #     lambda row: row["y"] if pd.notna(row["y"]) and row["date"].date() <= today else np.nan,
        #     axis=1
        # )

        display_df = filtered_df.rename(
            columns={
                "date": "Дата",
                "product_name": "Продукт",
                "region": "Регион",
                "y": "Факт. продажи",
                "yhat": "Прогноз",
                "yhat_lower": "Нижняя граница",
                "yhat_upper": "Верхняя граница",
            }
        )
        # Таблица
        st.subheader("Таблица прогнозов")
        st.dataframe(display_df, use_container_width=True)

        # Скачивание CSV
        st.download_button(
            "Скачать CSV",
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
            "Скачать Excel",
            data=towrite,
            file_name=f"forecast_{product}_{region}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with tab2:
    st.subheader("Метрики модели")

    # Фильтруем данные по продукту и региону
    metrics_filtered = metrics_df[
        (metrics_df["product_name"] == product) & (metrics_df["region"] == region)
    ].copy()

    if metrics_filtered.empty:
        st.warning("Нет метрик для выбранной комбинации.")
    else:
        # === Переименовываем колонки ===
        metrics_display = metrics_filtered.rename(
            columns={
                "model_name": "Модель",
                "product_name": "Продукт",
                "region": "Регион",
                "summ_error_3month": "bias",  # меняем имя в самих данных
            }
        )

        # Переводим заголовки для отображения (кроме mae, rmse, wape)
        metrics_display = metrics_display.rename(
            columns={
                "Модель": "Модель",
                "Продукт": "Продукт",
                "Регион": "Регион",
                "mae": "MAE",
                "rmse": "RMSE",
                "wape": "WAPE",
                "bias": "Bias",
            }
        )

        st.dataframe(metrics_display, use_container_width=True)

        st.markdown("""
        **Пояснение метрик:**

        - **MAE (Mean Absolute Error)** — показывает, насколько в среднем прогноз ошибается в единицах продаж.
        - **RMSE (Root Mean Squared Error)** — среднеквадратичная ошибка: чем больше выбросы, тем выше значение.
        - **WAPE (Weighted Absolute Percentage Error)** — взвешенная процентная ошибка, помогает понять, насколько прогноз близок к факту в относительном выражении.
        - **Bias (смещение прогноза)** — отражает систематическую ошибку: положительное значение — прогноз переоценивает продажи, отрицательное — недооценивает.
        """)
