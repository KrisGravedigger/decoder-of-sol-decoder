"""
Post-Close Analyzer for TP/SL Optimizer Phase 3B

Main analysis engine that coordinates LP valuation, fee simulation, and "what-if" analysis.
"""

import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
    from core.models import Position

from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
from reporting.lp_position_valuator import LPPositionValuator
from reporting.fee_simulator import FeeSimulator


logger = logging.getLogger(__name__)


class PostCloseAnalyzer:
    """
    Main analysis engine that coordinates LP valuation, fee simulation, and "what-if" analysis.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize post-close analyzer.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.cache_manager = EnhancedPriceCacheManager()
        self.fee_simulator = FeeSimulator(self.config)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
            
    def analyze_position_post_close(self, position: 'Position') -> Dict[str, Any]:
        """
        Complete post-close analysis for a single position.
        
        Steps:
        1. Apply scope filters (date, duration, close reason)
        2. Determine post-close time horizon
        3. Fetch post-close price and volume data
        4. Simulate fee allocation for extended period
        5. Calculate LP position values over timeline
        6. Identify optimal exit points and missed opportunities
        7. Generate ML-ready features
        
        Args:
            position: Position object to analyze
            
        Returns:
            Analysis results dictionary
        """
        # Initialize result
        result = {
            'position_id': position.position_id,
            'analysis_successful': False,
            'post_close_data_points': 0,
            'simulation_duration_hours': 0.0
        }
        
        try:
            # Step 1: Check if position passes scope filters
            if not self._passes_scope_filters(position):
                result['limitations'] = ['Position filtered out by scope configuration']
                return result
                
            # Step 2: Determine post-close time horizon
            end_datetime, extension_hours = self._calculate_post_close_period(position)
            result['simulation_duration_hours'] = extension_hours
            
            # Step 3: Fetch post-close data
            post_close_data = self.cache_manager.fetch_post_close_data(position, extension_hours)
            
            if not post_close_data:
                result['limitations'] = ['No post-close data available']
                return result
                
            result['post_close_data_points'] = len(post_close_data)
            
            # Step 4: Fetch position lifetime volume data for fee rate calculation
            position_volume_data = self.cache_manager.fetch_ochlv_data(
                position.pool_address, 
                position.open_timestamp, 
                position.close_timestamp,
                use_cache_only=True  # Should already be cached from previous analyses
            )

            # Simulate fee allocation using actual position fee rate
            allocated_fees = self.fee_simulator.calculate_fee_allocation(
                position, position_volume_data, post_close_data
            )
            
            # Step 5: Initialize LP valuator based on strategy
            strategy_parts = position.actual_strategy.split()
            strategy_type = "Bid-Ask" if "Bid-Ask" in position.actual_strategy else "Spot"
            step_size = "MEDIUM"  # Default
            for part in strategy_parts:
                if part.upper() in ["WIDE", "MEDIUM", "NARROW", "SIXTYNINE"]:
                    step_size = part.upper()
                    break
                    
            lp_valuator = LPPositionValuator(strategy_type, step_size)
            
            # Simulate position timeline
            timeline = lp_valuator.simulate_position_timeline(position, post_close_data, allocated_fees)
            
            if not timeline:
                result['limitations'] = ['Timeline simulation failed']
                return result
                
            # Step 6: Analyze timeline for optimal exit and missed opportunities
            analysis_results = self._analyze_timeline(position, timeline)
            
            # Update result with analysis
            result.update(analysis_results)
            result['analysis_successful'] = True
            
            # Step 7: Calculate ML features
            ml_features = self._calculate_ml_features(position, timeline, post_close_data)
            result.update(ml_features)
            
            # Determine confidence level
            result['simulation_confidence'] = self._determine_confidence(result)
            
        except Exception as e:
            logger.error(f"Post-close analysis failed for position {position.position_id}: {e}")
            result['limitations'] = [f'Analysis error: {str(e)}']
            
        return result
        
    def _passes_scope_filters(self, position: 'Position') -> bool:
        """
        Apply user-configured scope filters from tp_sl_analysis.scope_filters.
        
        Args:
            position: Position to check
            
        Returns:
            True if position passes all filters
        """
        scope_filters = self.config.get('tp_sl_analysis', {}).get('scope_filters', {})
        
        # Check close reason filter
        include_close_reasons = scope_filters.get('include_close_reasons', 
                                                 ["TP", "SL", "LV", "OOR", "other"])
        if position.close_reason not in include_close_reasons:
            return False
            
        # Check if excluding active positions
        if scope_filters.get('exclude_active_positions', True):
            if position.close_reason == 'active_at_log_end':
                return False
                
        # Check minimum duration
        min_duration_hours = scope_filters.get('min_position_duration_hours', 1)
        duration = (position.close_timestamp - position.open_timestamp).total_seconds() / 3600
        if duration < min_duration_hours:
            return False
            
        # Check minimum value
        min_value_sol = scope_filters.get('min_position_value_sol', 0.1)
        if position.initial_investment < min_value_sol:
            return False
            
        # Check date filter if enabled
        if scope_filters.get('enable_date_filter', False):
            # Check analysis_date_from
            date_from = scope_filters.get('analysis_date_from')
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                if position.close_timestamp < date_from:
                    return False
                    
            # Check last_n_days
            last_n_days = scope_filters.get('last_n_days')
            if last_n_days:
                cutoff_date = datetime.now() - timedelta(days=last_n_days)
                if position.close_timestamp < cutoff_date:
                    return False
                    
        return True
        
    def _calculate_post_close_period(self, position: 'Position') -> Tuple[datetime, float]:
        """
        Calculate optimal post-close analysis period.
        
        Returns:
            (end_datetime, analysis_hours)
        """
        config = self.config.get('tp_sl_analysis', {})
        
        position_duration = position.close_timestamp - position.open_timestamp
        default_extension = position_duration * config.get('post_close_multiplier', 1.0)
        
        # Apply min/max bounds
        min_hours = config.get('min_post_close_hours', 2)
        max_hours = config.get('max_post_close_hours', 48)
        
        extension_hours = max(min_hours, min(max_hours, default_extension.total_seconds() / 3600))
        
        end_datetime = position.close_timestamp + timedelta(hours=extension_hours)
        
        return end_datetime, extension_hours
        
    def _analyze_timeline(self, position: 'Position', timeline: List[Dict]) -> Dict[str, Any]:
        """
        Analyze simulated timeline for optimal exit points and missed opportunities.
        
        Args:
            position: Original position
            timeline: Simulated value timeline
            
        Returns:
            Analysis results
        """
        # Extract PnL percentages from timeline
        pnl_percentages = [point['pnl_pct'] for point in timeline]
        
        # Find peaks
        max_profit_idx = np.argmax(pnl_percentages)
        min_profit_idx = np.argmin(pnl_percentages)
        
        max_profit_post_close = pnl_percentages[max_profit_idx]
        max_loss_post_close = pnl_percentages[min_profit_idx]
        
        # Optimal exit analysis
        optimal_exit_idx = max_profit_idx
        optimal_exit_pnl = max_profit_post_close
        optimal_exit_time = timeline[optimal_exit_idx]['timestamp']
        
        # Calculate days to optimal exit
        days_to_optimal = (optimal_exit_time - position.close_timestamp).total_seconds() / 86400
        
        # Calculate missed opportunities
        actual_final_pnl_pct = (position.final_pnl / position.initial_investment * 100) if position.initial_investment > 0 else 0
        
        missed_upside_pct = max(0, optimal_exit_pnl - actual_final_pnl_pct)
        
        # For SL positions, calculate how much loss could have been avoided
        missed_downside_protection_pct = 0
        if position.close_reason == 'SL' and actual_final_pnl_pct < 0:
            # Find best exit before actual close
            pre_close_pnls = [p['pnl_pct'] for p in timeline if p['timestamp'] <= position.close_timestamp]
            if pre_close_pnls:
                best_pre_close = max(pre_close_pnls)
                missed_downside_protection_pct = best_pre_close - actual_final_pnl_pct
                
        return {
            'max_profit_post_close': max_profit_post_close,
            'max_loss_post_close': max_loss_post_close,
            'optimal_exit_time': optimal_exit_time,
            'optimal_exit_pnl_pct': optimal_exit_pnl,
            'days_to_optimal_exit': days_to_optimal,
            'missed_upside_pct': missed_upside_pct,
            'missed_downside_protection_pct': missed_downside_protection_pct,
        }
        
    def _calculate_ml_features(self, position: 'Position', timeline: List[Dict], 
                              price_data: List[Dict]) -> Dict[str, Any]:
        """
        Calculate ML-ready features for Phase 4.
        
        Args:
            position: Position object
            timeline: Value timeline
            price_data: Raw price data
            
        Returns:
            ML features dictionary
        """
        # Price volatility
        prices = [p['close'] for p in price_data]
        price_returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else []
        volatility_post_close = np.std(price_returns) * np.sqrt(24) if len(price_returns) > 0 else 0
        
        # Volume trend
        volumes = [p.get('volume', 0) for p in price_data]
        volume_trend = 'stable'
        if len(volumes) > 1:
            volume_change = (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] > 0 else 0
            if volume_change > 0.2:
                volume_trend = 'increasing'
            elif volume_change < -0.2:
                volume_trend = 'decreasing'
                
        # Price direction
        price_direction = 'neutral'
        if len(prices) > 1:
            price_change = (prices[-1] - prices[0]) / prices[0]
            if price_change > 0.05:
                price_direction = 'upward'
            elif price_change < -0.05:
                price_direction = 'downward'
                
        # Fee yield rate estimate
        total_fees = sum(point['accumulated_fees'] for point in timeline[-1:])
        fee_yield_rate = (total_fees / position.initial_investment / len(timeline) * 24) if position.initial_investment > 0 and len(timeline) > 0 else 0
        
        # Optimal TP/SL levels based on analysis
        optimal_tp_level = None
        optimal_sl_level = None
        
        # For TP optimization: find level that would have captured most upside
        pnl_percentages = [point['pnl_pct'] for point in timeline]
        if pnl_percentages:
            # Set optimal TP slightly below max to be realistic
            optimal_tp_level = max(pnl_percentages) * 0.9
            
            # Set optimal SL based on worst drawdown
            min_pnl = min(pnl_percentages)
            if min_pnl < 0:
                # Set SL with some buffer
                optimal_sl_level = abs(min_pnl) * 1.1
                
        return {
            'volatility_post_close': volatility_post_close,
            'volume_trend_post_close': volume_trend,
            'price_direction_post_close': price_direction,
            'fee_yield_rate_estimate': fee_yield_rate,
            'optimal_tp_level': optimal_tp_level,
            'optimal_sl_level': optimal_sl_level,
        }
        
    def _determine_confidence(self, result: Dict[str, Any]) -> str:
        """
        Determine confidence level for analysis results.
        
        Args:
            result: Analysis results
            
        Returns:
            'high', 'medium', or 'low'
        """
        # Check data coverage
        data_coverage = result.get('data_coverage_pct', 0)
        
        if data_coverage >= 90 and result.get('post_close_data_points', 0) >= 24:
            return 'high'
        elif data_coverage >= 70 and result.get('post_close_data_points', 0) >= 12:
            return 'medium'
        else:
            return 'low'
            
    def run_bulk_analysis(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run post-close analysis for filtered set of positions.
        
        Args:
            positions_df: DataFrame of positions to analyze
            
        Returns:
            Aggregated results and statistics
        """
        logger.info(f"Starting bulk post-close analysis for {len(positions_df)} positions...")
        
        # Apply scope filters
        filtered_df = self.apply_scope_filters(positions_df)
        logger.info(f"After filtering: {len(filtered_df)} positions to analyze")
        
        if filtered_df.empty:
            return {
                'total_positions': 0,
                'successful_analyses': 0,
                'positions_with_missed_upside': 0,
                'avg_missed_upside_pct': 0.0,
                'analysis_results': []
            }
            
        # Run analysis for each position
        results = []
        successful_count = 0
        total_missed_upside = 0.0
        positions_with_missed_upside = 0
        
        batch_size = self.config.get('tp_sl_analysis', {}).get('performance', {}).get('batch_size', 50)
        
        for i in range(0, len(filtered_df), batch_size):
            batch = filtered_df.iloc[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(filtered_df) + batch_size - 1)//batch_size}")
            
            for idx, row in batch.iterrows():
                # Convert row to position object (simplified)
                position = self._row_to_position(row)
                
                # Run analysis
                result = self.analyze_position_post_close(position)
                results.append(result)
                
                if result['analysis_successful']:
                    successful_count += 1
                    
                    if result.get('missed_upside_pct', 0) > 2.0:  # 2% threshold
                        positions_with_missed_upside += 1
                        total_missed_upside += result['missed_upside_pct']
                        
        # Calculate aggregate statistics
        avg_missed_upside = (total_missed_upside / positions_with_missed_upside) if positions_with_missed_upside > 0 else 0.0
        
        return {
            'total_positions': len(filtered_df),
            'successful_analyses': successful_count,
            'positions_with_missed_upside': positions_with_missed_upside,
            'avg_missed_upside_pct': avg_missed_upside,
            'analysis_results': results
        }
        
    def apply_scope_filters(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply user-configured scope filters from tp_sl_analysis.scope_filters.
        
        Args:
            positions_df: Input positions DataFrame
            
        Returns:
            Filtered DataFrame
        """
        filtered_df = positions_df.copy()
        scope_filters = self.config.get('tp_sl_analysis', {}).get('scope_filters', {})
        
        # Apply close reason filter
        include_close_reasons = scope_filters.get('include_close_reasons', 
                                                 ["TP", "SL", "LV", "OOR", "other"])
        filtered_df = filtered_df[filtered_df['close_reason'].isin(include_close_reasons)]
        
        # Exclude active positions if configured
        if scope_filters.get('exclude_active_positions', True):
            filtered_df = filtered_df[filtered_df['close_reason'] != 'active_at_log_end']
            
        # Apply minimum duration filter
        min_duration_hours = scope_filters.get('min_position_duration_hours', 1)
        duration_hours = (filtered_df['close_timestamp'] - filtered_df['open_timestamp']).dt.total_seconds() / 3600
        filtered_df = filtered_df[duration_hours >= min_duration_hours]
        
        # Apply minimum value filter
        min_value_sol = scope_filters.get('min_position_value_sol', 0.1)
        filtered_df = filtered_df[filtered_df['investment_sol'] >= min_value_sol]
        
        # Apply date filters if enabled
        if scope_filters.get('enable_date_filter', False):
            # Date from filter
            date_from = scope_filters.get('analysis_date_from')
            if date_from:
                date_from = pd.to_datetime(date_from)
                filtered_df = filtered_df[filtered_df['close_timestamp'] >= date_from]
                
            # Last N days filter
            last_n_days = scope_filters.get('last_n_days')
            if last_n_days:
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=last_n_days)
                filtered_df = filtered_df[filtered_df['close_timestamp'] >= cutoff_date]
                
        # Additional filter: require enough post-close time for analysis
        min_days_post_close = 7
        days_since_close = (pd.Timestamp.now() - filtered_df['close_timestamp']).dt.total_seconds() / 86400
        filtered_df = filtered_df[days_since_close >= min_days_post_close]
        
        return filtered_df
        
    def _row_to_position(self, row: pd.Series) -> Any:
        """
        Convert DataFrame row to position-like object for analysis.
        
        Args:
            row: DataFrame row
            
        Returns:
            Position-like object with required attributes
        """
        # Create a simple object with required attributes
        class SimplePosition:
            pass
            
        position = SimplePosition()
        
        # Map DataFrame columns to position attributes
        position.position_id = row['position_id']
        position.pool_address = row['pool_address']
        position.open_timestamp = row['open_timestamp']
        position.close_timestamp = row['close_timestamp']
        position.initial_investment = row['investment_sol']
        position.final_pnl = row['pnl_sol']
        position.close_reason = row['close_reason']
        position.actual_strategy = row['strategy_raw']
        position.total_fees_collected = row.get('total_fees_collected', 0.0)
        position.max_profit_during_position = row.get('max_profit_during_position')
        position.max_loss_during_position = row.get('max_loss_during_position')
        
        return position
        
    def generate_ml_features(self, analysis_results: List[Dict]) -> pd.DataFrame:
        """
        Generate ML-ready dataset for Phase 4 optimization.
        
        Args:
            analysis_results: List of analysis results from bulk analysis
            
        Returns:
            DataFrame ready for ML model training
        """
        features_list = []
        
        for result in analysis_results:
            if not result['analysis_successful']:
                continue
                
            # Extract features from result
            features = {
                # Identifiers
                'position_id': result['position_id'],
                
                # Position characteristics (would need to be added from position data)
                # These would come from joining with positions_df
                
                # Post-close analysis results
                'max_profit_post_close': result.get('max_profit_post_close', 0),
                'max_loss_post_close': result.get('max_loss_post_close', 0),
                'optimal_exit_pnl_pct': result.get('optimal_exit_pnl_pct', 0),
                'days_to_optimal_exit': result.get('days_to_optimal_exit', 0),
                
                # Missed opportunities
                'missed_upside_pct': result.get('missed_upside_pct', 0),
                'missed_downside_protection_pct': result.get('missed_downside_protection_pct', 0),
                
                # Market conditions
                'volatility_post_close': result.get('volatility_post_close', 0),
                'volume_trend_post_close': result.get('volume_trend_post_close', 'stable'),
                'price_direction_post_close': result.get('price_direction_post_close', 'neutral'),
                
                # Optimal parameters
                'optimal_tp_level': result.get('optimal_tp_level'),
                'optimal_sl_level': result.get('optimal_sl_level'),
                
                # Quality metrics
                'data_coverage_pct': result.get('data_coverage_pct', 0),
                'simulation_confidence': result.get('simulation_confidence', 'low'),
            }
            
            features_list.append(features)
            
        return pd.DataFrame(features_list)
        
    def export_ml_dataset(self, output_path: str = "ml_dataset_tp_sl.csv") -> str:
        """
        Export complete ML dataset for Phase 4 development.
        
        Args:
            output_path: Output CSV file path
            
        Returns:
            Path to exported CSV file
        """
        # Load positions
        from reporting.data_loader import load_and_prepare_positions
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        
        # Run bulk analysis
        bulk_results = self.run_bulk_analysis(positions_df)
        
        # Generate ML features
        ml_dataset = self.generate_ml_features(bulk_results['analysis_results'])
        
        # Join with position data for complete features
        # This would need to be implemented to merge position characteristics
        
        # Export to CSV
        ml_dataset.to_csv(output_path, index=False)
        logger.info(f"ML dataset exported to {output_path} with {len(ml_dataset)} records")
        
        return output_path