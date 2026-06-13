# -*- coding: utf-8 -*-
"""
Baseline XGBoost training and evaluation script.
Validates the synthetic dataset for machine learning workflows.
Trains:
1. An XGBoost Regressor to predict future grocery sales (quantity_sold).
2. An XGBoost Classifier to predict future stockout risk (stockout_occurred).
Uses a chronological train/test split to mirror real-world forecasting.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import classification_report, accuracy_score, f1_score


def load_and_preprocess():
    print("Loading datasets...")
    # Check if files exist
    if not os.path.exists("synthetic_kirana_dataset.csv"):
        raise FileNotFoundError(
            "synthetic_kirana_dataset.csv not found! Run 'generate_data.py' first."
        )

    df = pd.read_csv("synthetic_kirana_dataset.csv")
    df["date"] = pd.to_datetime(df["date"])

    # Identify categorical variables and encode them
    categorical_cols = [
        "store_id",
        "neighborhood_type",
        "product_name",
        "category",
        "festival_name",
    ]
    label_encoders = {}

    for col in categorical_cols:
        le = LabelEncoder()
        df[f"{col}_encoded"] = le.fit_transform(df[col])
        label_encoders[col] = le
        print(f"  Encoded categorical column: '{col}'")

    return df, label_encoders


def time_series_split(df):
    """
    Performs a chronological split:
    - Train: First 150 days (approx. Jan 1 to May 30)
    - Test: Last 30 days (approx. May 31 to June 29)
    This matches real-world forecasting setups and prevents future data leakage.
    """
    unique_dates = sorted(df["date"].unique())
    split_date = unique_dates[150]  # Start of last 30 days

    train_df = df[df["date"] < split_date]
    test_df = df[df["date"] >= split_date]

    print(f"\nTime Series Split:")
    print(
        f"  Training set : {train_df['date'].min().strftime('%Y-%m-%d')} to {train_df['date'].max().strftime('%Y-%m-%d')} ({train_df['date'].nunique()} days, {len(train_df):,} rows)"
    )
    print(
        f"  Testing set  : {test_df['date'].min().strftime('%Y-%m-%d')} to {test_df['date'].max().strftime('%Y-%m-%d')} ({test_df['date'].nunique()} days, {len(test_df):,} rows)"
    )

    return train_df, test_df


def train_sales_regressor(X_train, y_train, X_test, y_test, feature_names):
    """
    Trains an XGBoost Regressor to predict quantity_sold.
    """
    print("\n" + "=" * 25 + " TRAINING SALES REGRESSOR " + "=" * 25)

    # Instantiate the model with appropriate forecasting parameters
    reg = xgb.XGBRegressor(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )

    reg.fit(X_train, y_train)

    # Predict and evaluate
    y_pred_train = reg.predict(X_train)
    y_pred_test = reg.predict(X_test)

    # Clip predictions at 0 since sales cannot be negative
    y_pred_test = np.maximum(0, y_pred_test)
    y_pred_train = np.maximum(0, y_pred_train)

    # Compute metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    train_mae = mean_absolute_error(y_train, y_pred_train)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_r2 = r2_score(y_test, y_pred_test)

    print("Regression Performance Metrics:")
    print(f"  Train MAE  : {train_mae:.2f} units")
    print(f"  Test MAE   : {test_mae:.2f} units")
    print(f"  Train RMSE : {train_rmse:.2f} units")
    print(f"  Test RMSE  : {test_rmse:.2f} units")
    print(f"  Test R²    : {test_r2:.4f} (proportion of variance explained)")

    # Output Feature Importance
    importances = reg.feature_importances_
    indices = np.argsort(importances)[::-1]

    print("\nTop Feature Importances (Regressor):")
    for idx in indices[:8]:
        print(f"  - {feature_names[idx]:<22}: {importances[idx]:.4f}")


def train_stockout_classifier(X_train, y_train, X_test, y_test, feature_names):
    """
    Trains an XGBoost Classifier to predict stockout_occurred risk.
    """
    print("\n" + "=" * 25 + " TRAINING STOCKOUT RISK CLASSIFIER " + "=" * 25)

    # Calculate scale_pos_weight to handle class imbalance if present
    num_neg = np.sum(y_train == 0)
    num_pos = np.sum(y_train == 1)
    scale_weight = num_neg / num_pos if num_pos > 0 else 1.0

    clf = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_weight,
        random_state=42,
        n_jobs=-1,
    )

    clf.fit(X_train, y_train)

    # Predict and evaluate
    y_pred_test = clf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred_test)
    f1 = f1_score(y_test, y_pred_test)

    print("Classification Performance Metrics:")
    print(f"  Test Accuracy : {accuracy * 100:.2f}%")
    print(f"  Test F1-score : {f1:.4f}")
    print("\nDetailed Classification Report:")
    print(
        classification_report(
            y_test, y_pred_test, target_names=["In Stock", "Stockout"]
        )
    )

    # Output Feature Importance
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]

    print("Top Feature Importances (Classifier):")
    for idx in indices[:8]:
        print(f"  - {feature_names[idx]:<22}: {importances[idx]:.4f}")


if __name__ == "__main__":
    import os

    try:
        df, encoders = load_and_preprocess()
        train_df, test_df = time_series_split(df)

        # Define features.
        # We EXCLUDE unconstrained_demand, stock_level_morning, quantity_sold, stockout_occurred, and original string columns
        feature_cols = [
            "day_of_week",
            "month",
            "week_of_year",
            "is_weekend",
            "is_month_start",
            "is_salary_day",
            "is_festival",
            "is_rainy",
            "temperature",
            "base_daily_demand",
            "store_id_encoded",
            "neighborhood_type_encoded",
            "product_name_encoded",
            "category_encoded",
            "festival_name_encoded",
            "previous_day_sales",
            "rolling_7_day_average",
            "rolling_30_day_average",
        ]

        # Regression Targets
        X_train_reg = train_df[feature_cols].values
        y_train_reg = train_df["quantity_sold"].values
        X_test_reg = test_df[feature_cols].values
        y_test_reg = test_df["quantity_sold"].values

        train_sales_regressor(
            X_train_reg, y_train_reg, X_test_reg, y_test_reg, feature_cols
        )

        # Classification Targets
        X_train_clf = train_df[feature_cols].values
        y_train_clf = train_df["stockout_occurred"].values
        X_test_clf = test_df[feature_cols].values
        y_test_clf = test_df["stockout_occurred"].values

        train_stockout_classifier(
            X_train_clf, y_train_clf, X_test_clf, y_test_clf, feature_cols
        )

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
