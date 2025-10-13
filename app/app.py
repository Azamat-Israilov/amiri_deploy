import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import plotly.graph_objects as go

# ==========================
# Генерация синтетических данных
# ==========================
@st.cache_data
def generate_data(n_fact_days=60, n_forecast_days=90):
    products = ["Candy A", "Candy B", "Candy C"]
    regions = ["Север", "Запад"]

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

            # Прогнозные данные
            for d in forecast_dates:
                yhat = np.random.randint(90, 140)
                rows.append([d, product, region, None, yhat, yhat - 15, yhat + 15])

    return pd.DataFrame(
        rows,
        columns=["date", "product_name", "region", "y", "yhat", "yhat_lower", "yhat_upper"],
    )


@st.cache_data
def generate_model_metrics():
    rows = []
    for product in ["Candy A", "Candy B", "Candy C"]:
        for region in ["Север", "Юг", "Восток", "Запад"]:
            rows.append(
                [
                    "prophet",
                    np.round(np.random.uniform(5, 10), 2),
                    np.round(np.random.uniform(7, 12), 2),
                    np.round(np.random.uniform(1, 3), 2),
                    np.round(np.random.uniform(15, 30), 2),
                    product,
                    region,
                ]
            )
    return pd.DataFrame(
        rows,
        columns=["model_name", "mae", "rmse", "wape", "summ_error_3month", "product_name", "region"],
    )


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
# Фильтры
# ==========================
st.sidebar.header("Фильтры")
product = st.sidebar.selectbox("Выберите продукт", forecast_df["product_name"].unique())
region = st.sidebar.selectbox("Выберите регион", forecast_df["region"].unique())
horizon = st.sidebar.slider("Горизонт прогноза (дней)", 30, 90, 30)

# Отбираем нужный продукт и регион
filtered_df = forecast_df[
    (forecast_df["product_name"] == product) & (forecast_df["region"] == region)
].copy()

today = datetime.today().date()
fact_data = filtered_df[filtered_df["date"].dt.date <= today]
forecast_data = filtered_df[
    (filtered_df["date"].dt.date > today) &
    (filtered_df["date"].dt.date <= today + timedelta(days=horizon))
]

# Объединяем их обратно для графика (единая шкала)
filtered_df = pd.concat([fact_data, forecast_data]).sort_values("date")

# ==========================
# Вкладки
# ==========================
tab1, tab2 = st.tabs(["Прогноз vs Факт", "Метрики модели"])

# ==========================
# Вкладка 1 — Прогноз vs Факт
# ==========================
with tab1:
    st.subheader(f"Прогнозируемые vs Фактические продажи для {product} ({region})")

    if filtered_df.empty:
        st.warning("Нет данных для выбранных фильтров.")
    else:
        today = pd.Timestamp(datetime.today().date())

        fact_data = filtered_df[filtered_df["date"] <= today].dropna(subset=["y"])

        show_forecast = horizon != 30

        forecast_all = filtered_df.dropna(subset=["yhat"]).copy()
        if show_forecast:
            max_forecast_date = today + pd.Timedelta(days=horizon)
            forecast_vis = forecast_all[forecast_all["date"] <= max_forecast_date]
        else:
            forecast_vis = pd.DataFrame(columns=forecast_all.columns)

        fig = go.Figure()

        # Факт (всегда)
        if not fact_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=fact_data["date"],
                    y=fact_data["y"],
                    mode="lines+markers",
                    name="Факт",
                    line=dict(color="#1f77b4", width=3),
                    marker=dict(size=4),
                    hovertemplate="<b>Дата:</b> %{x|%d %b %Y}<br><b>Продажи (факт):</b> %{y:.0f}<extra></extra>",
                )
            )

        # Прогноз (наложение на прошлое + будущее до горизонта)
        if show_forecast and not forecast_vis.empty:
            fig.add_trace(
                go.Scatter(
                    x=forecast_vis["date"],
                    y=forecast_vis["yhat"],
                    mode="lines+markers",
                    name="Прогноз",
                    line=dict(color="#ff7f0e", width=3, dash="dash"),
                    marker=dict(size=4),
                    hovertemplate="<b>Дата:</b> %{x|%d %b %Y}<br><b>Продажи (прогноз):</b> %{y:.0f}<extra></extra>",
                )
            )

            # Доверительный интервал (там, где есть границы)
            ci = forecast_vis.dropna(subset=["yhat_lower", "yhat_upper"])
            if not ci.empty:
                fig.add_trace(
                    go.Scatter(
                        x=ci["date"],
                        y=ci["yhat_upper"],
                        mode="lines",
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=ci["date"],
                        y=ci["yhat_lower"],
                        mode="lines",
                        line=dict(width=0),
                        fill="tonexty",
                        fillcolor="rgba(255, 127, 14, 0.2)",
                        name="Доверительный интервал",
                        hoverinfo="skip",
                    )
                )

        # Вертикальная линия "Сегодня"
        fig.add_shape(
            type="line",
            x0=today, x1=today,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="gray", width=2, dash="dot"),
        )
        fig.add_annotation(
            x=today, y=1, xref="x", yref="paper",
            text="Сегодня", showarrow=False, yanchor="bottom",
            font=dict(size=12, color="gray"),
        )

        fig.update_layout(
            # title=f"Прогноз vs Факт для {product} ({region})",
            xaxis_title="Дата",
            yaxis_title="Продажи",
            template="plotly_white",
            height=500,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                showgrid=True, gridwidth=1, gridcolor="lightgray",
                tickformat="%d %b",
                range=[filtered_df["date"].min(), filtered_df["date"].max()],
                nticks=8,
            ),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor="lightgray"),
        )

        st.plotly_chart(fig, use_container_width=True)


        # === Таблица и экспорт ===
        display_df = filtered_df.rename(
            columns={
                "date": "Дата",
                "product_name": "Продукт",
                "region": "Регион",
                "y": "Факт. Продажи",
                "yhat": "Прогноз модели",
                "yhat_lower": "Минимально ожидаемые продажи",
                "yhat_upper": "Максимально ожидаемые продажи",
            }
        )

        st.subheader("Таблица прогнозов")
        st.dataframe(display_df, use_container_width=True)

        st.download_button(
            "Скачать CSV",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"forecast_{product}_{region}.csv",
            mime="text/csv",
        )

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

# ==========================
# Вкладка 2 — Метрики модели
# ==========================
with tab2:
    st.subheader("Метрики модели")

    metrics_filtered = metrics_df[
        (metrics_df["product_name"] == product) & (metrics_df["region"] == region)
    ].copy()

    if metrics_filtered.empty:
        st.warning("Нет метрик для выбранной комбинации.")
    else:
        metrics_display = metrics_filtered.rename(
            columns={
                "model_name": "Модель",
                "product_name": "Продукт",
                "region": "Регион",
                "summ_error_3month": "Bias",
                "mae": "MAE",
                "rmse": "RMSE",
                "wape": "WAPE",
            }
        )

        st.dataframe(metrics_display, use_container_width=True)

        st.markdown("""
        ### Пояснение метрик

        - **MAE (Средняя ошибка прогноза)** — показывает, насколько в среднем прогноз отличается от факта.  
        *Чем меньше значение, тем точнее модель.*

        - **RMSE (Ошибка с учётом выбросов)** — аналог MAE, но сильнее реагирует на резкие скачки в данных.  
        *Если RMSE заметно выше MAE, значит модель иногда сильно промахивается.*

        - **WAPE (Процент ошибки прогноза)** — доля ошибки прогноза в процентах от общего объёма продаж.  
        *Например, WAPE = 10 % означает, что модель ошибается примерно на 10 % от реальных продаж.*

        - **Bias (Смещение прогноза)** — показывает, в какую сторону модель систематически ошибается.  
        *Положительное значение — переоценивает спрос, отрицательное — недооценивает.*
        """)
