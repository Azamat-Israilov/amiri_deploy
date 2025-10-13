import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import test_connection
from app.data_access import (
    fetch_products_and_regions,
    fetch_forecast_vs_actual,
    fetch_metrics,
)


# ==========================
# Fallback data for demo purposes
# ==========================
@st.cache_data
def get_demo_products_regions():
    """Return demo products and regions for fallback"""
    return ["Candy A", "Candy B", "Candy C"], ["north", "south", "east", "west"]


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
db_ok = test_connection()
if db_ok:
    try:
        products, regions = fetch_products_and_regions()
    except Exception:
        products, regions = get_demo_products_regions()
else:
    products, regions = get_demo_products_regions()

# ==========================
# Фильтры (sidebar)
# ==========================
st.sidebar.header("Фильтры")

product = st.sidebar.selectbox("Выберите продукт", products)
region = st.sidebar.selectbox("Выберите регион", regions)
horizon = st.sidebar.slider("Горизонт прогноза (дней)", 1, 90, 30)

# Получаем данные
if db_ok:
    try:
        filtered_df = fetch_forecast_vs_actual(product, region, horizon)
        metrics_df = fetch_metrics(product, region)
    except Exception:
        st.warning("⚠️ Ошибка подключения к базе данных. Используйте демо-режим.")
        filtered_df = pd.DataFrame()
        metrics_df = pd.DataFrame()
else:
    st.info("ℹ️ База данных недоступна. Используйте демо-режим.")
    filtered_df = pd.DataFrame()
    metrics_df = pd.DataFrame()

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

        # Создаем Plotly график
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
                    hovertemplate="<b>Факт</b><br>Дата: %{x}<br>Продажи: %{y}<extra></extra>",
                )
            )

        # Прогноз
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
                    hovertemplate="<b>Прогноз</b><br>Дата: %{x}<br>Продажи: %{y}<extra></extra>",
                )
            )

            # Доверительный интервал
            if not forecast_data.dropna(subset=["yhat_lower", "yhat_upper"]).empty:
                fig.add_trace(
                    go.Scatter(
                        x=forecast_data["date"],
                        y=forecast_data["yhat_upper"],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=forecast_data["date"],
                        y=forecast_data["yhat_lower"],
                        mode="lines",
                        line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(255, 127, 14, 0.2)",
                        name="Доверительный интервал",
                        hoverinfo="skip",
                    )
                )

        # Настройка макета
        fig.update_layout(
            title=f"Прогноз vs Факт для {product} ({region})",
            xaxis_title="Дата",
            yaxis_title="Продажи",
            template="plotly_white",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor="lightgray",
                tickformat="%d %b",
                # Показывать только даты где есть данные
                range=[filtered_df["date"].min(), filtered_df["date"].max()],
                # Уменьшаем количество тиков
                nticks=8,
            ),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor="lightgray"),
        )

        st.plotly_chart(fig, width="stretch")

        # Таблица
        st.subheader("Таблица прогнозов")
        st.dataframe(filtered_df, width="stretch")

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

    metrics_filtered = (
        metrics_df[
            (metrics_df["product_name"] == product) & (metrics_df["region"] == region)
        ]
        if not metrics_df.empty
        else metrics_df
    )

    if metrics_filtered.empty:
        st.warning("⚠️ Нет метрик для выбранной комбинации.")
    else:
        st.dataframe(metrics_filtered, width="stretch")
