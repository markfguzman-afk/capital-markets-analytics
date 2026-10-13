"""
01_premarket_advisory/reprice_monitor.py

Real-Time Fractional Tick Parser & Asymmetric Desk Reprice Monitor.
Author: Mark Guzman (Plaza Home Mortgage Desk Veteran)

Translates institutional Agency MBS (UMBS) fractional tick conventions 
(e.g., 101-14+, 100-28 3/8) into decimal pricing and monitors intraday 
market movements against asymmetric desk reprice thresholds.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RepriceAlert:
    security: str
    baseline_price: float
    current_price: float
    delta_bps: float
    action: str
    severity: str


class FractionalTickParser:
    """
    Parses fixed-income 32nds pricing conventions into decimal values.
    
    Standard industry representations:
      - '101-16'   -> 101 + 16/32 = 101.500000
      - '101-16+'  -> 101 + 16.5/32 = 101.515625 (plus sign = 1/64)
      - '101-162'  -> 101 + 16.25/32 = 101.5078125 (quarter-tick)
      - '101-166'  -> 101 + 16.75/32 = 101.5234375 (three-quarter-tick)
      - '101-16 3/8' -> 101 + (16 + 3/8)/32 = 101.51171875
    """

    @staticmethod
    def parse_to_decimal(tick_str: str) -> float:
        clean_str = tick_str.strip()
        pattern = r"^(\d+)-(\d{2})([+26]|\s
