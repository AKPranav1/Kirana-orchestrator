# -*- coding: utf-8 -*-
"""
Feature engineering module.
Contains functions for creating date features, simulating seasonal weather, and
calculating robust, group-by lag and rolling features without data leakage.
"""

import numpy as np
import pandas as pd
from src.config import RANDOM_SEED, FESTIVAL_EVENTS


def generate_weather_series(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Simulates daily seasonal weather for an Indian city.
    - Temperature follows a smooth sine wave (cool in Jan, peaking in May, slightly cooler in June).
    - Rainy days are simulated with month-based Bernoulli probabilities (monsoon ramping up in June).
    - Temperature drops on rainy days.
    """
    np.random.seed(RANDOM_SEED)
    weather_records = []

    for i, date in enumerate(dates):
        month = date.month

        # 1. Determine rain probability by month
        if month in [1, 2]:
            rain_prob = 0.05  # Dry winter
        elif month in [3, 4]:
            rain_prob = 0.02  # Dry spring
        elif month in [5]:
            rain_prob = 0.15  # Pre-monsoon showers
        else:  # June
            rain_prob = 0.45  # Early monsoon season

        is_rainy = 1 if np.random.random() < rain_prob else 0

        # 2. Temperature baseline trend (sine wave peaking in mid-May, t ~ 135)
        # Ranges from around 18°C in January to 41°C in May
        base_temp = 18.0 + 23.0 * np.sin((np.pi * i) / 240.0)

        # Add random daily variation
        temp = base_temp + np.random.normal(0, 1.5)

        # Cooling effect of rain (drops temperature by 3°C to 6°C)
        if is_rainy:
            temp -= np.random.uniform(3.0, 6.0)

        # Keep temperature within realistic physical boundaries for India
        temp = max(10.0, min(temp, 47.0))

        weather_records.append(
            {"date": date, "is_rainy": is_rainy, "temperature": round(temp, 1)}
        )

    return pd.DataFrame(weather_records)


def extract_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts date-related features from the date column.
    Includes day of week, month, week of year, weekend indicators, salary day flags,
    and festival markers.
    """
    df = df.copy()
    # Ensure date is datetime type
    df["date"] = pd.to_datetime(df["date"])

    # Standard calendar features
    df["day_of_week"] = df["date"].dt.dayofweek  # Monday=0, Sunday=6
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)

    # Weekend indicator (Saturday=5, Sunday=6)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # Month start indicator
    df["is_month_start"] = df["date"].dt.is_month_start.astype(int)

    # Salary days: Indian salaries are usually paid on the 1st or the 15th (mid-month cash infusion)
    df["is_salary_day"] = df["date"].dt.day.isin([1, 15]).astype(int)

    # Festival features
    df["is_festival"] = 0
    df["festival_name"] = "None"

    # Map dates to festivals from configuration
    for date_str, festival_info in FESTIVAL_EVENTS.items():
        match_mask = df["date"] == pd.to_datetime(date_str)
        df.loc[match_mask, "is_festival"] = 1
        df.loc[match_mask, "festival_name"] = festival_info["name"]

    return df


def calculate_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates historical lag and rolling sales features within each store-product group.
    To prevent data leakage, we shift the quantity_sold by 1 day BEFORE computing
    the rolling averages. This guarantees that prediction on day t only uses historical
    sales up to day t-1.

    Features:
    - previous_day_sales (sales on t-1)
    - rolling_7_day_average (mean sales of t-1 to t-7)
    - rolling_30_day_average (mean sales of t-1 to t-30)

    Fills NaNs with the store-product specific average of quantity_sold across the dataset.
    """
    df = df.copy()

    # Crucial step: Sort chronologically within each group to ensure correct sequence
    df = df.sort_values(by=["store_id", "product_name", "date"]).reset_index(drop=True)

    # Group series to calculate lags
    group = df.groupby(["store_id", "product_name"])["quantity_sold"]

    # 1. Previous Day Sales (shift of 1)
    df["previous_day_sales"] = group.shift(1)

    # 2. Rolling averages calculated on the shifted (previous) day sales to avoid leakage
    # We use min_periods=1 to compute averages even with partial history at the series start
    df["rolling_7_day_average"] = df.groupby(["store_id", "product_name"])[
        "previous_day_sales"
    ].transform(lambda x: x.rolling(window=7, min_periods=1).mean())

    df["rolling_30_day_average"] = df.groupby(["store_id", "product_name"])[
        "previous_day_sales"
    ].transform(lambda x: x.rolling(window=30, min_periods=1).mean())

    # 3. Handle missing values at the beginning of each series
    # To make the data ready for model training, we impute NaN values using the overall mean of
    # quantity_sold for that specific store and product.
    group_means = df.groupby(["store_id", "product_name"])["quantity_sold"].transform(
        "mean"
    )

    df["previous_day_sales"] = df["previous_day_sales"].fillna(group_means)
    df["rolling_7_day_average"] = df["rolling_7_day_average"].fillna(group_means)
    df["rolling_30_day_average"] = df["rolling_30_day_average"].fillna(group_means)

    return df
