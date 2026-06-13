# -*- coding: utf-8 -*-
"""
Master script to run the synthetic data generation pipeline.
Saves the generated datasets to CSV files and outputs basic statistics.
"""

import os
import time
from src.generator import KiranaDataGenerator


def main():
    print("=" * 60)
    print("STARTING INDIAN KIRANA STORE SYNTHETIC DATA GENERATOR")
    print("=" * 60)

    start_time = time.time()

    # Instantiate and execute the generator
    generator = KiranaDataGenerator()
    dataset_df, stores_df, products_df = generator.generate_all()

    elapsed_time = time.time() - start_time
    print(f"\nSimulation completed successfully in {elapsed_time:.2f} seconds!")

    # Save files to the current directory
    print("\nSaving datasets to CSV files...")

    dataset_path = "synthetic_kirana_dataset.csv"
    stores_path = "stores.csv"
    products_path = "products.csv"

    dataset_df.to_csv(dataset_path, index=False)
    stores_df.to_csv(stores_path, index=False)
    products_df.to_csv(products_path, index=False)

    print(f"  Saved: {dataset_path} ({len(dataset_df):,} rows)")
    print(f"  Saved: {stores_path} ({len(stores_df):,} rows)")
    print(f"  Saved: {products_path} ({len(products_df):,} rows)")

    # Display basic descriptive diagnostics
    print("\n" + "=" * 30 + " DIAGNOSTICS " + "=" * 30)
    print(f"Total row count         : {len(dataset_df)}")
    print(f"Unique stores           : {dataset_df['store_id'].nunique()}")
    print(f"Unique products         : {dataset_df['product_name'].nunique()}")
    print(
        f"Date range              : {dataset_df['date'].min().strftime('%Y-%m-%d')} to {dataset_df['date'].max().strftime('%Y-%m-%d')} ({dataset_df['date'].nunique()} days)"
    )

    total_sales = dataset_df["quantity_sold"].sum()
    total_demand = dataset_df["unconstrained_demand"].sum()
    fulfilled_rate = (total_sales / total_demand) * 100 if total_demand > 0 else 0
    stockout_rows = dataset_df["stockout_occurred"].sum()
    stockout_rate = (stockout_rows / len(dataset_df)) * 100

    print(f"Total quantity demanded : {total_demand:,} units")
    print(f"Total quantity sold     : {total_sales:,} units")
    print(f"Demand fulfillment rate : {fulfilled_rate:.2f}%")
    print(
        f"Total stockout incidents : {stockout_rows:,} rows ({stockout_rate:.2f}% of all transactions)"
    )

    print("\nNeighborhood Type Distribution of Sales:")
    sales_by_neigh = dataset_df.groupby("neighborhood_type")["quantity_sold"].mean()
    for neigh, avg_sales in sales_by_neigh.items():
        print(f"  - {neigh:<18} : {avg_sales:.2f} average units/day per transaction")

    print("\nTop 5 Categories by Sales Volume:")
    sales_by_cat = (
        dataset_df.groupby("category")["quantity_sold"]
        .sum()
        .sort_values(ascending=False)
    )
    for cat, total_volume in sales_by_cat.head(5).items():
        print(f"  - {cat:<20} : {total_volume:,} total units sold")

    print("=" * 73)


if __name__ == "__main__":
    main()
