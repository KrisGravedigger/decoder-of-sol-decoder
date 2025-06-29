"""
Metrics Calculator for Portfolio Analytics

Provides functions to calculate key performance indicators (KPIs) for a
portfolio of trading positions, in both SOL and USDC denominations.
"""

import logging
from typing import Dict, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def calculate_daily_returns(positions_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily portfolio returns from positions."""
    if positions_df.empty:
        return pd.DataFrame()

    daily_pnl = positions_df.groupby(positions_df['close_timestamp'].dt.date)['pnl_sol'].sum()
    daily_df = daily_pnl.reset_index()
    daily_df.columns = ['date', 'daily_pnl_sol']
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    daily_df = daily_df.sort_values('date').reset_index(drop=True)
    daily_df['cumulative_pnl_sol'] = daily_df['daily_pnl_sol'].cumsum()

    # Estimate capital base for return calculation
    avg_investment = positions_df['investment_sol'].mean() if not positions_df.empty else 1.0
    estimated_capital_base = avg_investment * len(positions_df) if not positions_df.empty else 1.0
    daily_df['daily_return'] = daily_df['daily_pnl_sol'] / estimated_capital_base

    return daily_df

def calculate_sol_metrics(positions_df: pd.DataFrame, daily_df: pd.DataFrame, risk_free_rate: float) -> Dict[str, float]:
    """Calculate portfolio metrics in SOL denomination."""
    if positions_df.empty or daily_df.empty:
        return _empty_metrics()

    total_pnl_sol = positions_df['pnl_sol'].sum()
    win_rate = (positions_df['pnl_sol'] > 0).mean()

    positive_pnl = positions_df[positions_df['pnl_sol'] > 0]['pnl_sol'].sum()
    negative_pnl = abs(positions_df[positions_df['pnl_sol'] < 0]['pnl_sol'].sum())
    profit_factor = positive_pnl / negative_pnl if negative_pnl > 0 else float('inf')

    # Sharpe ratio
    sharpe_ratio = 0.0
    if len(daily_df) > 1 and daily_df['daily_return'].std() > 0:
        daily_returns = daily_df['daily_return']
        risk_free_daily = risk_free_rate / 365
        excess_returns = daily_returns - risk_free_daily
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(365)

    # Max drawdown
    max_drawdown = 0.0
    if len(daily_df) > 1 and not daily_df['cumulative_pnl_sol'].expanding().max().eq(0).all():
        cumulative = daily_df['cumulative_pnl_sol']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max.abs().replace(0, np.nan)
        max_drawdown = drawdown.min() * 100

    # Net PnL
    total_cost_sol = positions_df['infrastructure_cost_sol'].sum() if 'infrastructure_cost_sol' in positions_df.columns else 0
    net_pnl_sol = total_pnl_sol - total_cost_sol

    return {
        'total_pnl_sol': total_pnl_sol, 'sharpe_ratio': sharpe_ratio,
        'max_drawdown_percent': max_drawdown, 'win_rate': win_rate,
        'profit_factor': profit_factor, 'net_pnl_after_costs': net_pnl_sol,
        'total_positions': len(positions_df)
    }

def calculate_usdc_metrics(positions_df: pd.DataFrame, sol_rates: Dict[str, float], risk_free_rate: float) -> Dict[str, float]:
    """Calculate portfolio metrics in USDC denomination."""
    if positions_df.empty:
        return _empty_metrics()

    positions_usdc = positions_df.copy()
    positions_usdc['pnl_usdc'] = positions_usdc.apply(
        lambda row: row['pnl_sol'] * sol_rates.get(row['close_timestamp'].strftime("%Y-%m-%d"), 0),
        axis=1
    )
    if 'infrastructure_cost_sol' in positions_usdc.columns:
        positions_usdc['infrastructure_cost_usdc'] = positions_usdc.apply(
            lambda row: row['infrastructure_cost_sol'] * sol_rates.get(row['close_timestamp'].strftime("%Y-%m-%d"), 0),
            axis=1
        )
    else:
        positions_usdc['infrastructure_cost_usdc'] = 0.0

    # Daily USDC returns
    daily_pnl_usdc = positions_usdc.groupby(positions_usdc['close_timestamp'].dt.date)['pnl_usdc'].sum()
    daily_usdc_df = daily_pnl_usdc.reset_index()
    daily_usdc_df.columns = ['date', 'daily_pnl_usdc']
    daily_usdc_df['date'] = pd.to_datetime(daily_usdc_df['date'])
    daily_usdc_df['cumulative_pnl_usdc'] = daily_usdc_df['daily_pnl_usdc'].cumsum()

    # Estimate capital base for return calculation
    avg_investment_sol = positions_df['investment_sol'].mean() if not positions_df.empty else 1.0
    avg_sol_price = np.mean(list(sol_rates.values())) if sol_rates else 150
    estimated_capital_base_usdc = avg_investment_sol * len(positions_df) * avg_sol_price
    daily_usdc_df['daily_return'] = daily_usdc_df['daily_pnl_usdc'] / estimated_capital_base_usdc

    total_pnl_usdc = positions_usdc['pnl_usdc'].sum()
    win_rate = (positions_usdc['pnl_usdc'] > 0).mean()

    positive_pnl = positions_usdc[positions_usdc['pnl_usdc'] > 0]['pnl_usdc'].sum()
    negative_pnl = abs(positions_usdc[positions_usdc['pnl_usdc'] < 0]['pnl_usdc'].sum())
    profit_factor = positive_pnl / negative_pnl if negative_pnl > 0 else float('inf')

    # Sharpe ratio
    sharpe_ratio = 0.0
    if len(daily_usdc_df) > 1 and daily_usdc_df['daily_return'].std() > 0:
        daily_returns = daily_usdc_df['daily_return']
        risk_free_daily = risk_free_rate / 365
        excess_returns = daily_returns - risk_free_daily
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(365)

    # Max drawdown
    max_drawdown = 0.0
    if len(daily_usdc_df) > 1 and not daily_usdc_df['cumulative_pnl_usdc'].expanding().max().eq(0).all():
        cumulative = daily_usdc_df['cumulative_pnl_usdc']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max.abs().replace(0, np.nan)
        max_drawdown = drawdown.min() * 100

    total_cost_usdc = positions_usdc['infrastructure_cost_usdc'].sum()
    net_pnl_usdc = total_pnl_usdc - total_cost_usdc

    return {
        'total_pnl_usdc': total_pnl_usdc, 'sharpe_ratio': sharpe_ratio,
        'max_drawdown_percent': max_drawdown, 'win_rate': win_rate,
        'profit_factor': profit_factor, 'net_pnl_after_costs': net_pnl_usdc,
        'total_positions': len(positions_usdc)
    }

def calculate_currency_comparison(sol_rates: Dict[str, float], sol_metrics: Dict[str, float], usdc_metrics: Dict[str, float], positions_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate currency comparison metrics."""
    if not sol_rates:
        return {'sol_price_change_period': 0.0, 'outperformance_vs_hodl': 0.0, 'preferred_denomination': 'SOL'}

    rates_list = sorted(sol_rates.items())
    sol_price_change = 0.0
    if len(rates_list) >= 2:
        start_price = rates_list[0][1]
        end_price = rates_list[-1][1]
        if start_price > 0:
            sol_price_change = (end_price - start_price) / start_price * 100

    total_investment_sol = positions_df['investment_sol'].sum() if not positions_df.empty else 1.0
    lp_return_pct = (sol_metrics.get('total_pnl_sol', 0) / total_investment_sol * 100) if total_investment_sol > 0 else 0
    outperformance = lp_return_pct - sol_price_change

    preferred = 'SOL' if sol_metrics.get('sharpe_ratio', 0) >= usdc_metrics.get('sharpe_ratio', 0) else 'USDC'

    return {
        'sol_price_change_period': sol_price_change,
        'outperformance_vs_hodl': outperformance,
        'preferred_denomination': preferred
    }

def _empty_metrics() -> Dict[str, float]:
    """Return empty metrics structure for edge cases."""
    return {
        'total_pnl_sol': 0.0, 'total_pnl_usdc': 0.0, 'sharpe_ratio': 0.0,
        'max_drawdown_percent': 0.0, 'win_rate': 0.0, 'profit_factor': 0.0,
        'net_pnl_after_costs': 0.0, 'total_positions': 0
    }