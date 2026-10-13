"""
02_pipeline_hedging/dv01_hedge_allocator.py

Pipeline Fallout Pull-Through Modeling & Short TBA DV01 Immunization.
Author: Mark Guzman (Plaza Home Mortgage Desk Veteran)

Models mortgage pipeline pull-through probability using logistic regression,
computes net DV01 exposure, and allocates short Agency UMBS forward contracts 
to immunize duration risk across dynamic coupon stacks.
"""

from dataclasses import dataclass
from typing import Dict, List
import numpy as np


@dataclass
class PipelineLoan:
    loan_id: str
    note_rate: float
    current_market_rate: float
    upb: float
    days_to_close: int
    is_purchase: bool
    dv01_per_million: float  # Dollar value of an 01 (bps) per $1M UPB


@dataclass
class TBAContract:
    coupon: float
    settlement_month: str
    price: float
    dv01_per_million: float  # DV01 of the hedging instrument


class PullThroughEstimator:
    """
    Empirical logistic model predicting pull-through probability
    conditioned on rate incentive, pipeline age/days to close, and loan purpose.
    """

    def __init__(
        self,
        intercept: float = 1.25,
        beta_spread: float = -2.85,  # Higher market rate relative to note rate reduces fallout
        beta_days: float = -0.025,   # Longer days to close increases fallout risk
        beta_purchase: float = 0.65, # Purchase loans have higher commitment/pull-through
    ):
        self.intercept = intercept
        self.beta_spread = beta_spread
        self.beta_days = beta_days
        self.beta_purchase = beta_purchase

    def predict_probability(self, loan: PipelineLoan) -> float:
        # Rate incentive = (Current Market Rate - Locked Note Rate)
        # If market rate drops below note rate, borrower has incentive to renegotiate/fall out
        rate_incentive = loan.current_market_rate - loan.note_rate
        
        logit = (
            self.intercept
            + (self.beta_spread * rate_incentive)
            + (self.beta_days * loan.days_to_close)
            + (self.beta_purchase if loan.is_purchase else 0.0)
        )
        # Sigmoid link function
        prob = 1.0 / (1.0 + np.exp(-logit))
        return float(np.clip(prob, 0.05, 0.98))


class HedgeAllocator:
    """
    Computes effective pull-through weighted pipeline DV01 and allocates
    short TBA forward contracts to maintain target hedge coverage ratios.
    """

    def __init__(self, target_coverage_ratio: float = 1.00):
        self.target_coverage_ratio = target_coverage_ratio

    def calculate_pipeline_dv01(
        self,
        pipeline: List[PipelineLoan],
        estimator: PullThroughEstimator,
    ) -> Dict[str, float]:
        total_upb = 0.0
        weighted_upb = 0.0
        total_dv01 = 0.0

        for loan in pipeline:
            pt_prob = estimator.predict_probability(loan)
            eff_upb = loan.upb * pt_prob
            loan_dv01 = (eff_upb / 1_000_000.0) * loan.dv01_per_million

            total_upb += loan.upb
            weighted_upb += eff_upb
            total_dv01 += loan_dv01

        return {
            "gross_upb": round(total_upb, 2),
            "effective_weighted_upb": round(weighted_upb, 2),
            "net_pipeline_dv01": round(total_dv01, 2),
            "aggregate_pull_through": round(weighted_upb / total_upb, 4) if total_upb else 0.0,
        }

    def solve_tba_short_allocation(
        self,
        net_pipeline_dv01: float,
        tba: TBAContract,
    ) -> Dict[str, float]:
        target_hedge_dv01 = net_pipeline_dv01 * self.target_coverage_ratio
        
        # Calculate millions required to neutralize pipeline DV01
        required_tba_millions = target_hedge_dv01 / tba.dv01_per_million
        contract_count = round(required_tba_millions)

        return {
            "target_hedge_dv01": round(target_hedge_dv01, 2),
            "recommended_short_upb": round(required_tba_millions * 1_000_000.0, 2),
            "recommended_contracts_1m": contract_count,
            "residual_dv01_leakage": round(
                target_hedge_dv01 - (contract_count * tba.dv01_per_million), 2
            ),
        }


# --------------------------------------------------------------------------
# Demonstration & Desk Smoke Test
# --------------------------------------------------------------------------
if __name__ == "__main__":
    estimator = PullThroughEstimator()
    allocator = HedgeAllocator(target_coverage_ratio=1.00)

    # Sample pipeline snapshot
    sample_pipeline = [
        PipelineLoan("LN-1001", note_rate=6.125, current_market_rate=6.250, upb=450_000, days_to_close=18, is_purchase=True, dv01_per_million=420.0),
        PipelineLoan("LN-1002", note_rate=6.375, current_market_rate=6.250, upb=620_000, days_to_close=35, is_purchase=False, dv01_per_million=445.0),
        PipelineLoan("LN-1003", note_rate=6.250, current_market_rate=6.250, upb=510_000, days_to_close=12, is_purchase=True, dv01_per_million=430.0),
        PipelineLoan("LN-1004", note_rate=6.000, current_market_rate=6.250, upb=380_000, days_to_close=25, is_purchase=True, dv01_per_million=415.0),
    ]

    metrics = allocator.calculate_pipeline_dv01(sample_pipeline, estimator)
    
    print("--- PIPELINE RISK & FALLOUT ANALYSIS ---")
    print(f"Gross Pipeline UPB:       ${metrics['gross_upb']:,.2f}")
    print(f"Pull-Through Weighted UPB: ${metrics['effective_weighted_upb']:,.2f}")
    print(f"Aggregate Pull-Through:    {metrics['aggregate_pull_through']*100:.2f}%")
    print(f"Net Pipeline DV01:         ${metrics['net_pipeline_dv01']:,.2f} / bp")

    # Hedge instrument: UMBS 30Y 5.5% forward
    hedge_instrument = TBAContract(coupon=5.5, settlement_month="Nov26", price=101.50, dv01_per_million=435.0)
    trade_plan = allocator.solve_tba_short_allocation(metrics["net_pipeline_dv01"], hedge_instrument)

    print("\n--- RECOMMENDED TBA HEDGE POSITION ---")
    print(f"Hedge Instrument:          UMBS {hedge_instrument.coupon}% {hedge_instrument.settlement_month}")
    print(f"Recommended Short UPB:     ${trade_plan['recommended_short_upb']:,.2f}")
    print(f"Standard $1M Contracts:    {trade_plan['recommended_contracts_1m']} contracts short")
    print(f"Residual DV01 Leakage:     ${trade_plan['residual_dv01_leakage']:+.2f} / bp")
