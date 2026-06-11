"""
PlanParams dataclass — replaces the g module's global state.
All plan-level and tier-level parameters live here.
Tier-specific fields (COLA, BenefitFactor, etc.) are updated per tier call
via dataclasses.replace(params, COLA=..., BenefitFactor=...).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class PlanParams:
    # Grid dimensions
    EmployeeStart: int = 20
    EmployeeEnd: int = 74
    ServiceStart: int = 1
    ServiceEnd: int = 55
    Nyear: int = 35
    NMonte: int = 1

    # Economic assumptions
    WageGrowth: float = 0.0
    Inflation: float = 0.0
    discountrate: float = 0.07
    rf: float = 0.02
    PopulationGrowth: float = 0.01
    scaling: float = 1.0
    annuity_dr: float = 0.02

    # Contribution / payout rates
    EmployeeContributionRate: float = 0.0
    EmployerContributionRate: float = 0.0
    DisabilityPayoutRate: float = 0.025
    refundReturn: float = 0.0

    # Survivor / mortality adjustments
    pct_mrg: float = 0.5
    widow_reduct: float = 0.5
    MortAdujst: float = 1.0   # sic — kept to match R
    pctmale: float = 0.5

    # Tier-specific fields (set per tier via dataclasses.replace)
    COLA: float = 0.0
    WageYears: int = 5
    BenefitCap: float = float('inf')
    BenefitFactor: float = 0.0
    RetirementStart: int = 60
    NyearFullBenefit: int = 5

    # Rate tables — must be set before any simulation call
    SeparationRate:  Optional[np.ndarray] = field(default=None, repr=False)
    RefundRate:      Optional[np.ndarray] = field(default=None, repr=False)
    RetirementRate:  Optional[np.ndarray] = field(default=None, repr=False)
    MortalityTable:  Optional[np.ndarray] = field(default=None, repr=False)
    AnnuityVector:   Optional[np.ndarray] = field(default=None, repr=False)
