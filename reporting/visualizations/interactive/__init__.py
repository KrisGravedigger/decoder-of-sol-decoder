"""
Re-exports interactive chart functions to provide a unified import interface.

This allows other modules to import all chart functions from
`reporting.visualizations.interactive` instead of from the individual
sub-modules, simplifying imports and maintenance.
"""

from .market_charts import (
    create_correlation_chart,
    create_trend_performance_chart,
    create_ema_trend_chart,
)

from .portfolio_charts import (
    create_metrics_summary_chart,
    create_professional_equity_curve,
    create_professional_drawdown_analysis,
    create_professional_cost_impact,
)

from .simulation_charts import (
    create_weekend_comparison_chart,
    create_weekend_distribution_chart,
    create_strategy_simulation_chart,
)

from .strategy_charts import (
    create_professional_strategy_heatmap,
    create_strategy_avg_pnl_summary,
)

__all__ = [
    # Market Charts
    "create_correlation_chart",
    "create_trend_performance_chart",
    "create_ema_trend_chart",
    
    # Portfolio Charts
    "create_metrics_summary_chart",
    "create_professional_equity_curve",
    "create_professional_drawdown_analysis",
    "create_professional_cost_impact",
    
    # Simulation Charts
    "create_weekend_comparison_chart",
    "create_weekend_distribution_chart",
    "create_strategy_simulation_chart",
    
    # Strategy Charts
    "create_professional_strategy_heatmap",
    "create_strategy_avg_pnl_summary",
]