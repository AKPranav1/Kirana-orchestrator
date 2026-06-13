# -*- coding: utf-8 -*-
"""
Main synthetic data generator module.
Combines store, product, date, and weather features, runs the physics-of-demand
vectorized simulation, and executes a high-speed matrix-based inventory stock decay
and periodic replenishment simulation.
"""

import numpy as np
import pandas as pd
from src.config import (
    RANDOM_SEED,
    STORES,
    PRODUCTS,
    START_DATE,
    NUM_DAYS,
    NEIGHBORHOOD_MULTIPLIERS,
    WEEKEND_MULTIPLIER,
    SALARY_DAY_MULTIPLIER,
    FESTIVAL_EVENTS,
    WEATHER_MULTIPLIERS,
    MONTHLY_BASE_MULTIPLIERS,
    MONTHLY_CATEGORY_SEASONALITY,
    REPLENISHMENT_CYCLE_DAYS,
    SAFETY_FACTOR,
)
from src.features import (
    generate_weather_series,
    extract_date_features,
    calculate_lag_features,
)


class KiranaDataGenerator:
    """
    Simulator for an Indian Kirana store demand forecasting system.
    Generates a realistic synthetic dataset across stores, products, and days.
    """

    def __init__(self):
        self.random_seed = RANDOM_SEED
        self.stores_df = pd.DataFrame(STORES)
        self.products_df = pd.DataFrame(PRODUCTS)

        # Parse start date and generate a date range of exactly 180 days
        self.start_date = pd.to_datetime(START_DATE)
        self.dates = pd.date_range(start=self.start_date, periods=NUM_DAYS, freq="D")

    def generate_all(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Coordinates the entire data generation process:
        1. Generates base stores and products dataframes.
        2. Builds the Cartesian product of (stores x products x dates).
        3. Simulates daily weather and joins feature tables.
        4. Calculates expected and noisy unconstrained demand.
        5. Simulates inventory replenishment and stockout events.
        6. Engineers lag and rolling average features.

        Returns:
            df_final: The full synthetic dataset of 90,000 rows.
            stores_df: Master list of stores.
            products_df: Master list of products.
        """
        np.random.seed(self.random_seed)

        # 1. Create Cartesian product (Stores x Products x Dates)
        print("Generating core combinations...")
        cartesian_index = pd.MultiIndex.from_product(
            [self.stores_df["store_id"], self.products_df["product_name"], self.dates],
            names=["store_id", "product_name", "date"],
        )
        df = pd.DataFrame(index=cartesian_index).reset_index()

        # 2. Join store and product feature metadata
        df = df.merge(self.stores_df, on="store_id", how="left")
        df = df.merge(self.products_df, on="product_name", how="left")

        # 3. Generate daily weather profile and join on date
        print("Simulating weather...")
        weather_df = generate_weather_series(self.dates)
        df = df.merge(weather_df, on="date", how="left")

        # 4. Extract calendar/date features
        print("Extracting date and festival features...")
        df = extract_date_features(df)

        # 5. Vectorized Multiplier Calculations
        print("Calculating demand multipliers...")
        df = self._apply_multipliers(df)

        # 6. Simulate Inventory & Sales (Stockout Simulation)
        print("Running inventory and stockout simulation...")
        df = self._simulate_inventory(df)

        # 7. Feature Engineering: Lags and Rolling Averages
        print("Generating historical lag features...")
        df = calculate_lag_features(df)

        # Rearrange columns to keep it clean and intuitive
        columns_order = [
            "store_id",
            "neighborhood_type",
            "date",
            "day_of_week",
            "month",
            "week_of_year",
            "is_weekend",
            "is_month_start",
            "is_salary_day",
            "is_festival",
            "festival_name",
            "is_rainy",
            "temperature",
            "product_name",
            "category",
            "base_daily_demand",
            "unconstrained_demand",
            "stock_level_morning",
            "quantity_sold",
            "stockout_occurred",
            "previous_day_sales",
            "rolling_7_day_average",
            "rolling_30_day_average",
        ]
        df = df[columns_order]

        return df, self.stores_df, self.products_df

    def _apply_multipliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs vectorized calculations of the demand multipliers based on
        behavior guidelines, weather patterns, and seasonality.
        """
        df = df.copy()

        # 1. Neighborhood Multiplier
        # Pre-build a fast lookup dictionary mapping (neighborhood_type, product_name) -> value
        neigh_map = {}
        for n_type in self.stores_df["neighborhood_type"].unique():
            n_config = NEIGHBORHOOD_MULTIPLIERS.get(n_type, {})
            for p_name in self.products_df["product_name"]:
                neigh_map[(n_type, p_name)] = n_config.get(
                    p_name, n_config.get("DEFAULT", 1.0)
                )

        # Fast vectorized map
        df["neighborhood_multiplier"] = df.set_index(
            ["neighborhood_type", "product_name"]
        ).index.map(neigh_map)

        # 2. Weekend Multiplier
        df["weekend_multiplier"] = np.where(
            df["is_weekend"] == 1, WEEKEND_MULTIPLIER, 1.0
        )

        # 3. Salary Day Multiplier
        df["salary_multiplier"] = np.where(
            df["is_salary_day"] == 1, SALARY_DAY_MULTIPLIER, 1.0
        )

        # 4. Festival Multiplier (product-specific festive peaks)
        fest_map = {}
        for date_str, fest_info in FESTIVAL_EVENTS.items():
            boosts = fest_info.get("boosts", {})
            for p_name in self.products_df["product_name"]:
                # If product is specifically boosted, use that, else general festive lift of 1.1x
                fest_map[(pd.to_datetime(date_str), p_name)] = boosts.get(p_name, 1.1)

        df["festival_multiplier"] = (
            df.set_index(["date", "product_name"]).index.map(fest_map).fillna(1.0)
        )

        # 5. Weather Multiplier (rainy day effects)
        rain_config = WEATHER_MULTIPLIERS.get("rainy", {})
        rain_map = {
            p_name: rain_config.get(p_name, rain_config.get("DEFAULT", 0.95))
            for p_name in self.products_df["product_name"]
        }
        df["weather_multiplier"] = 1.0
        rainy_mask = df["is_rainy"] == 1
        df.loc[rainy_mask, "weather_multiplier"] = df.loc[
            rainy_mask, "product_name"
        ].map(rain_map)

        # 6. Monthly Seasonality Multiplier (including category/product specific seasonal shapes)
        seasonal_map = {}
        for month in range(1, 7):  # Jan-June
            base_mult = MONTHLY_BASE_MULTIPLIERS.get(month, 1.0)
            for p_name in self.products_df["product_name"]:
                p_row = self.products_df[
                    self.products_df["product_name"] == p_name
                ].iloc[0]
                category = p_row["category"]

                # Check for category-level monthly seasonality first
                if category in MONTHLY_CATEGORY_SEASONALITY:
                    val = MONTHLY_CATEGORY_SEASONALITY[category].get(month, base_mult)
                # Check for product-specific monthly seasonality
                elif p_name in MONTHLY_CATEGORY_SEASONALITY:
                    val = MONTHLY_CATEGORY_SEASONALITY[p_name].get(month, base_mult)
                else:
                    val = base_mult

                seasonal_map[(month, p_name)] = val

        df["seasonality_multiplier"] = (
            df.set_index(["month", "product_name"]).index.map(seasonal_map).fillna(1.0)
        )

        # 7. Calculate Deterministic Expected Demand
        df["expected_demand"] = (
            df["base_daily_demand"]
            * df["neighborhood_multiplier"]
            * df["weekend_multiplier"]
            * df["salary_multiplier"]
            * df["festival_multiplier"]
            * df["weather_multiplier"]
            * df["seasonality_multiplier"]
        )

        # 8. Introduce Heteroskedastic Gaussian Noise (variance scales with magnitude of expected demand)
        # 12% standard deviation relative to expected demand
        noise_std = df["expected_demand"] * 0.12
        noise = np.random.normal(0, noise_std)

        # Ensure demand is rounded to integer and is non-negative
        df["unconstrained_demand"] = np.maximum(
            0, np.round(df["expected_demand"] + noise)
        ).astype(int)

        # Drop temporary multipliers to keep final dataset clean
        df = df.drop(
            columns=[
                "neighborhood_multiplier",
                "weekend_multiplier",
                "salary_multiplier",
                "festival_multiplier",
                "weather_multiplier",
                "seasonality_multiplier",
                "expected_demand",
            ]
        )

        return df

    def _simulate_inventory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulates stock levels and quantity sold over time in a highly optimized manner.
        We sort the dataframe chronologically within each (store, product) group.
        This allows us to reshape the unconstrained demand into a (500, 180) matrix
        and simulate stock depletion and replenishment in single-digit milliseconds.
        """
        df = df.copy()

        # CRITICAL: Sort by store, product, date to align rows perfectly
        df = df.sort_values(by=["store_id", "product_name", "date"]).reset_index(
            drop=True
        )

        num_stores = len(self.stores_df)
        num_products = len(self.products_df)
        num_groups = num_stores * num_products  # 20 * 25 = 500 groups
        num_days = NUM_DAYS  # 180 days

        # Calculate maximum inventory capacity for each group
        # Cap = ceil(base_demand * neighborhood_multiplier * replenishment_cycle * safety_factor)
        # This represents how much inventory a store is willing to carry for a product
        max_inventories = np.zeros(num_groups)

        # Build lookup array for groups
        group_idx = 0
        for store_id in self.stores_df["store_id"]:
            store_neigh = self.stores_df[self.stores_df["store_id"] == store_id][
                "neighborhood_type"
            ].iloc[0]
            n_config = NEIGHBORHOOD_MULTIPLIERS.get(store_neigh, {})

            for p_name in self.products_df["product_name"]:
                base_demand = self.products_df[
                    self.products_df["product_name"] == p_name
                ]["base_daily_demand"].iloc[0]
                neigh_mult = n_config.get(p_name, n_config.get("DEFAULT", 1.0))

                # Average daily demand under this store's neighborhood type
                avg_daily_demand = base_demand * neigh_mult

                # Max stock capacity
                max_stock = np.ceil(
                    avg_daily_demand * REPLENISHMENT_CYCLE_DAYS * SAFETY_FACTOR
                )
                max_inventories[group_idx] = max(
                    5.0, max_stock
                )  # Ensure a minimum stock of 5 units
                group_idx += 1

        # Extract unconstrained demand as a 2D matrix: shape (500, 180)
        demand_matrix = df["unconstrained_demand"].values.reshape(num_groups, num_days)

        # Pre-allocate result matrices
        stock_morning = np.zeros((num_groups, num_days))
        quantity_sold = np.zeros((num_groups, num_days))
        stockout_occurred = np.zeros((num_groups, num_days), dtype=int)

        # Initial stock level (stores start fully stocked on Day 0)
        current_stock = max_inventories.copy()

        # Run daily step-by-step stock updates
        for t in range(num_days):
            # 1. Replenish morning stock if it's a delivery day
            # Delivery arrives every REPLENISHMENT_CYCLE_DAYS (e.g., every 3 days)
            if t % REPLENISHMENT_CYCLE_DAYS == 0:
                current_stock = max_inventories.copy()

            stock_morning[:, t] = current_stock

            # 2. Daily demand fulfillment
            demand_t = demand_matrix[:, t]
            sold_t = np.minimum(demand_t, current_stock)

            quantity_sold[:, t] = sold_t
            stockout_occurred[:, t] = (demand_t > current_stock).astype(int)

            # 3. Stock at the end of the day is updated for tomorrow
            current_stock = current_stock - sold_t

        # Flatten matrices back to align with df
        df["stock_level_morning"] = stock_morning.reshape(-1).astype(int)
        df["quantity_sold"] = quantity_sold.reshape(-1).astype(int)
        df["stockout_occurred"] = stockout_occurred.reshape(-1)

        return df
