# Capital Markets Analytics & Quantitative Trading Suite

Developed by **Mark Guzman** (8-year Secondary Marketing desk veteran at Plaza Home Mortgage; B.A. Quantitative Research & Behavioral Modeling, UC Irvine), this repository bridges frontline institutional fixed-income trading operations with automated programmatic modeling.

It provides production-ready tools for mortgage pipeline risk management, whole-loan pricing, Assignment of Trade (AOT) execution, Best Execution optimization, and loan-level color analytics.

---

## Architecture Overview

```text
capital-markets-analytics/
├── 01_premarket_advisory/
│   └── reprice_monitor.py           # 32nds fractional tick parser & intraday reprice alert engine
├── 02_pipeline_hedging/
│   └── dv01_hedge_allocator.py      # Logistic fallout pull-through model & short TBA DV01 immunization
├── 03_sql_analytics/
│   └── cover_spread_analytics.sql   # Relational schema & queries for whole-loan bid color & cover spreads
├── 04_aot_llpa_engine/
│   └── aot_trade_confirmation.py    # Multi-tier LLPA grid parser & tri-party AOT pair-off savings generator
└── 05_best_ex_allocator/
    └── best_execution_solver.py     # Linear programming allocator across GSE Cash Windows & aggregators
