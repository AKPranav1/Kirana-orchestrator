# -*- coding: utf-8 -*-
"""
Configuration module for the Indian Kirana Store Demand Forecasting System.
Contains reproducible random seed, store list, product catalog, weather baselines,
festival calendars, and demand multipliers.
"""

# Reproducible random seed
RANDOM_SEED = 42

# Date Range Configuration (180 Days starting Jan 1, 2026)
START_DATE = "2026-01-01"
NUM_DAYS = 180

# Inventory Policy Constants
REPLENISHMENT_CYCLE_DAYS = 3
SAFETY_FACTOR = 1.5

# Store configurations (20 stores, 5 of each neighborhood type)
NEIGHBORHOOD_TYPES = [
    "college_campus",
    "family_suburb",
    "office_district",
    "mixed_residential",
]

STORES = [
    {"store_id": "STORE_01", "neighborhood_type": "college_campus"},
    {"store_id": "STORE_02", "neighborhood_type": "college_campus"},
    {"store_id": "STORE_03", "neighborhood_type": "college_campus"},
    {"store_id": "STORE_04", "neighborhood_type": "college_campus"},
    {"store_id": "STORE_05", "neighborhood_type": "college_campus"},
    {"store_id": "STORE_06", "neighborhood_type": "family_suburb"},
    {"store_id": "STORE_07", "neighborhood_type": "family_suburb"},
    {"store_id": "STORE_08", "neighborhood_type": "family_suburb"},
    {"store_id": "STORE_09", "neighborhood_type": "family_suburb"},
    {"store_id": "STORE_10", "neighborhood_type": "family_suburb"},
    {"store_id": "STORE_11", "neighborhood_type": "office_district"},
    {"store_id": "STORE_12", "neighborhood_type": "office_district"},
    {"store_id": "STORE_13", "neighborhood_type": "office_district"},
    {"store_id": "STORE_14", "neighborhood_type": "office_district"},
    {"store_id": "STORE_15", "neighborhood_type": "office_district"},
    {"store_id": "STORE_16", "neighborhood_type": "mixed_residential"},
    {"store_id": "STORE_17", "neighborhood_type": "mixed_residential"},
    {"store_id": "STORE_18", "neighborhood_type": "mixed_residential"},
    {"store_id": "STORE_19", "neighborhood_type": "mixed_residential"},
    {"store_id": "STORE_20", "neighborhood_type": "mixed_residential"},
]

# Product Catalog (25 products, realistic Indian grocery items and categories)
PRODUCTS = [
    # Staples (6 products)
    {"product_name": "Rice", "category": "Staples", "base_daily_demand": 20},
    {"product_name": "Wheat Flour", "category": "Staples", "base_daily_demand": 25},
    {"product_name": "Cooking Oil", "category": "Staples", "base_daily_demand": 15},
    {"product_name": "Sugar", "category": "Staples", "base_daily_demand": 18},
    {"product_name": "Dal", "category": "Staples", "base_daily_demand": 14},
    {"product_name": "Salt", "category": "Staples", "base_daily_demand": 8},
    # Dairy (4 products)
    {"product_name": "Milk", "category": "Dairy", "base_daily_demand": 55},
    {"product_name": "Curd", "category": "Dairy", "base_daily_demand": 25},
    {"product_name": "Paneer", "category": "Dairy", "base_daily_demand": 12},
    {"product_name": "Butter", "category": "Dairy", "base_daily_demand": 15},
    # Snacks & Beverages (7 products)
    {
        "product_name": "Maggi",
        "category": "Snacks & Beverages",
        "base_daily_demand": 45,
    },
    {
        "product_name": "Bread",
        "category": "Snacks & Beverages",
        "base_daily_demand": 30,
    },
    {
        "product_name": "Soft drinks",
        "category": "Snacks & Beverages",
        "base_daily_demand": 25,
    },
    {
        "product_name": "Chips",
        "category": "Snacks & Beverages",
        "base_daily_demand": 40,
    },
    {
        "product_name": "Biscuits",
        "category": "Snacks & Beverages",
        "base_daily_demand": 35,
    },
    {"product_name": "Tea", "category": "Snacks & Beverages", "base_daily_demand": 35},
    {
        "product_name": "Coffee",
        "category": "Snacks & Beverages",
        "base_daily_demand": 15,
    },
    # Personal Care (3 products)
    {"product_name": "Soap", "category": "Personal Care", "base_daily_demand": 12},
    {"product_name": "Shampoo", "category": "Personal Care", "base_daily_demand": 8},
    {
        "product_name": "Toothpaste",
        "category": "Personal Care",
        "base_daily_demand": 10,
    },
    # Household (2 products)
    {"product_name": "Detergent", "category": "Household", "base_daily_demand": 15},
    {
        "product_name": "Tomato Ketchup",
        "category": "Snacks & Beverages",
        "base_daily_demand": 10,
    },
    {"product_name": "Spices", "category": "Staples", "base_daily_demand": 10},
    # Fresh Produce (2 products)
    {"product_name": "Onions", "category": "Fresh Produce", "base_daily_demand": 30},
    {"product_name": "Potatoes", "category": "Fresh Produce", "base_daily_demand": 35},
]

# Behavior Multipliers

# 1. Neighborhood Multipliers
# Specific products get large boosts, while non-core products might be slightly depressed.
NEIGHBORHOOD_MULTIPLIERS = {
    "college_campus": {
        "Maggi": 2.0,
        "Bread": 1.8,
        "Soft drinks": 2.2,
        "Chips": 2.0,
        "Biscuits": 1.5,
        "DEFAULT": 0.8,  # Students buy fewer core household staples
    },
    "family_suburb": {
        "Rice": 1.8,
        "Milk": 1.7,
        "Cooking Oil": 1.9,
        "Sugar": 1.6,
        "Soap": 1.5,
        "DEFAULT": 1.0,  # standard demand for others
    },
    "office_district": {
        "Tea": 2.2,
        "Coffee": 2.2,
        "Biscuits": 1.6,
        "Bread": 1.5,
        "DEFAULT": 0.7,  # Very low demand for main cooking ingredients/staples
    },
    "mixed_residential": {
        # High-density mixed neighborhoods have slightly higher volume for all products
        "DEFAULT": 1.1,
    },
}

# 2. Temporal Multipliers
WEEKEND_MULTIPLIER = 1.2  # 20% sales boost on Saturday and Sunday
SALARY_DAY_MULTIPLIER = 1.3  # 30% sales boost on 1st and 15th (salary days)

# 3. Weather Effects
# Rainy day triggers hot snack / beverage craving and discourages store visits for other items.
WEATHER_MULTIPLIERS = {
    "rainy": {
        "Tea": 1.4,
        "Coffee": 1.4,
        "Maggi": 1.3,
        "Soft drinks": 0.7,
        "DEFAULT": 0.95,  # Slight reduction due to rain keeping people indoors
    }
}

# 4. Indian Festivals Calendar (Jan - June 2026)
# Maps specific dates to festival names and product-specific multipliers
FESTIVAL_EVENTS = {
    "2026-01-14": {
        "name": "Makar Sankranti / Pongal",
        "boosts": {
            "Rice": 2.0,
            "Sugar": 1.8,
            "Cooking Oil": 1.5,
            "Spices": 1.5,
            "Milk": 1.4,
        },
    },
    "2026-01-15": {
        "name": "Makar Sankranti / Pongal",
        "boosts": {
            "Rice": 2.0,
            "Sugar": 1.8,
            "Cooking Oil": 1.5,
            "Spices": 1.5,
            "Milk": 1.4,
        },
    },
    "2026-02-15": {
        "name": "Maha Shivratri",
        "boosts": {"Milk": 2.2, "Curd": 1.8, "Sugar": 1.5, "Paneer": 1.6},
    },
    "2026-03-03": {
        "name": "Holi Warm-up",
        "boosts": {
            "Soft drinks": 1.5,
            "Chips": 1.4,
            "Biscuits": 1.3,
            "Milk": 1.3,
            "Sugar": 1.4,
        },
    },
    "2026-03-04": {
        "name": "Holi Festival",
        "boosts": {
            "Soft drinks": 2.2,
            "Chips": 1.8,
            "Biscuits": 1.5,
            "Milk": 1.8,
            "Cooking Oil": 1.7,
            "Sugar": 1.8,
            "Spices": 1.4,
        },
    },
    "2026-03-20": {
        "name": "Eid-ul-Fitr",
        "boosts": {
            "Rice": 2.0,
            "Milk": 1.8,
            "Sugar": 1.8,
            "Cooking Oil": 1.6,
            "Spices": 1.7,
            "Dal": 1.5,
        },
    },
    "2026-03-27": {
        "name": "Ram Navami",
        "boosts": {"Milk": 1.6, "Sugar": 1.5, "Cooking Oil": 1.4, "Paneer": 1.4},
    },
    "2026-04-14": {
        "name": "Vaisakhi / Poila Boishakh",
        "boosts": {
            "Rice": 1.8,
            "Sugar": 1.6,
            "Cooking Oil": 1.5,
            "Paneer": 1.8,
            "Milk": 1.5,
            "Spices": 1.5,
        },
    },
}

# 5. General and Category-Specific Monthly Seasonality
# Models month-by-month temperature/weather changes and cultural buying cycles
# Month index: 1 (Jan) to 12 (Dec). We generate Jan-June (1-6).
MONTHLY_BASE_MULTIPLIERS = {
    1: 0.95,  # Slow post-New Year
    2: 1.00,  # Standard
    3: 1.02,  # Start of warm season
    4: 1.05,  # School holidays, higher snack consumption
    5: 1.03,  # Peak summer
    6: 0.98,  # Start of monsoons, transitions
}

# Product/Category adjustments by month
MONTHLY_CATEGORY_SEASONALITY = {
    "Dairy": {
        # High summer demand for curd, paneer, and ice cold dairy
        1: 0.8,
        2: 0.9,
        3: 1.1,
        4: 1.4,
        5: 1.5,
        6: 1.2,
    },
    "Soft drinks": {
        # Extreme temperature dependency
        1: 0.6,
        2: 0.8,
        3: 1.2,
        4: 1.6,
        5: 1.8,
        6: 1.3,
    },
    "Tea": {
        # Hot drinks are consumed more in cooler weather and rainy season
        1: 1.3,
        2: 1.2,
        3: 0.9,
        4: 0.8,
        5: 0.8,
        6: 1.1,
    },
    "Coffee": {
        # Similar to Tea
        1: 1.3,
        2: 1.1,
        3: 0.9,
        4: 0.8,
        5: 0.8,
        6: 1.1,
    },
}
