"""
Configuration and constants for the Financial Resilience Engine.
Sheridan Datathon 2026 - Tangerine Track
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))

# CPI snapshot supplied by the comparison ZIP; retained for reference-model parity.
# This snapshot is not a live/independently verified Statistics Canada feed.
# Covers 2020-01 to 2025-12
CANADIAN_CPI_INDEX = {
    # 2020
    "2020-01": 136.8, "2020-02": 137.4, "2020-03": 136.6, "2020-04": 135.7,
    "2020-05": 136.1, "2020-06": 137.2, "2020-07": 137.2, "2020-08": 137.0,
    "2020-09": 136.9, "2020-10": 137.5, "2020-11": 137.7, "2020-12": 137.4,
    # 2021
    "2021-01": 138.2, "2021-02": 138.9, "2021-03": 139.6, "2021-04": 140.3,
    "2021-05": 141.0, "2021-06": 141.4, "2021-07": 142.3, "2021-08": 142.6,
    "2021-09": 142.9, "2021-10": 143.9, "2021-11": 144.2, "2021-12": 144.0,
    # 2022
    "2022-01": 145.3, "2022-02": 146.8, "2022-03": 148.9, "2022-04": 149.8,
    "2022-05": 151.9, "2022-06": 152.9, "2022-07": 153.1, "2022-08": 152.6,
    "2022-09": 153.2, "2022-10": 154.3, "2022-11": 155.0, "2022-12": 153.1,
    # 2023
    "2023-01": 153.9, "2023-02": 154.5, "2023-03": 155.3, "2023-04": 156.4,
    "2023-05": 157.0, "2023-06": 157.2, "2023-07": 158.2, "2023-08": 158.8,
    "2023-09": 158.7, "2023-10": 158.8, "2023-11": 159.0, "2023-12": 158.8,
    # 2024
    "2024-01": 158.8, "2024-02": 159.3, "2024-03": 160.2, "2024-04": 161.0,
    "2024-05": 161.9, "2024-06": 161.7, "2024-07": 162.3, "2024-08": 162.0,
    "2024-09": 161.4, "2024-10": 162.0, "2024-11": 162.3, "2024-12": 162.5,
    # 2025
    "2025-01": 163.4, "2025-02": 164.2, "2025-03": 164.8, "2025-04": 165.5,
    "2025-05": 166.0, "2025-06": 166.4, "2025-07": 167.1, "2025-08": 167.3,
    "2025-09": 167.5, "2025-10": 167.9, "2025-11": 168.2, "2025-12": 168.6,
}

# Expense Pyramid Ideal Targets
EXPENSE_PYRAMID_TARGETS = {
    "base": 0.50,    # 50% Essential fixed costs (household bills, loan payments, insurance)
    "middle": 0.30,  # 30% Flexible necessary living costs (groceries, transit, utilities)
    "peak": 0.20,    # 20% Discretionary / non-essential spending
}

# Behavioral Fraud Configuration
FRAUD_CONFIG = {
    "flag_threshold": 0.85,
    "new_store_baseline": 0.50,
    "cart_z_threshold": 3.0,
    "cart_z_anomaly_penalty": 0.35,
    "recurring_discount_rate": 0.10,
    "browsing_context_discount": 0.15,
    "chargeback_penalty_each": 0.10,
    "location_distance_penalty": 0.25,
    "budget_exceeded_penalty": 0.10,
}

# Installment Plan Configurations
INSTALLMENT_PLANS = [
    {
        "term_months": 3,
        "fee_type": "FLAT_FEE",
        "fee_amount": 30.00,
        "apr": 0.0,
        "description": "3-Month Relief: $30 flat fee, 0% APR"
    },
    {
        "term_months": 6,
        "fee_type": "INTEREST",
        "rate": 0.085,
        "apr": 8.50,
        "description": "6-Month Stabilizer: 8.50% APR structured installment"
    },
    {
        "term_months": 12,
        "fee_type": "INTEREST",
        "rate": 0.099,
        "apr": 9.90,
        "description": "12-Month Extended: 9.90% APR budget protection plan"
    }
]

# API Keys & Third-Party Config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Rachel (professional & empathetic)
