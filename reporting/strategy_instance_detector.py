import pandas as pd
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import hashlib
import math
import yaml
import os

# AIDEV-NOTE-CLAUDE: Core module for grouping positions into strategy instances
# Business logic: group by strategy+tp+sl with a 4-day time gap rule

logger = logging.getLogger('StrategyInstanceDetector')

class StrategyInstanceDetector:
    """
    Detects and groups positions into strategy instances based on parameters.
    
    A strategy instance is a unique combination of:
    - strategy (exact match)
    - takeProfit (exact match) 
    - stopLoss (exact match)
    A new instance is created if the same parameter set is used after a 4-day gap.
    """
    
    def __init__(self):
        """
        Initialize detector.
        """
        self.strategy_instances: Dict[str, Dict[str, Any]] = {}
        self.position_to_instance: Dict[str, str] = {}
        
    def _generate_strategy_id(self, strategy: str, tp: float, sl: float, first_use_date: datetime, last_use_date: Optional[datetime] = None) -> str:
        """
        Generate unique strategy instance ID without end dates.
        Format: {strategy}_TP{tp}_SL{sl}_{YYYY-MM-DD}_{hash}
        """
        # AIDEV-NOTE-GEMINI: Added NaN check to prevent crashes.
        if pd.isna(tp):
            tp_formatted = 'NaN'
        else:
            tp_formatted = int(tp) if tp == int(tp) else round(tp, 1)

        if pd.isna(sl):
            sl_formatted = 'NaN'
        else:
            sl_formatted = int(sl) if sl == int(sl) else round(sl, 1)

        strategy_base = f"{strategy}_TP{tp_formatted}_SL{sl_formatted}"
        start_date_str = first_use_date.strftime('%Y-%m-%d')
        
        # AIDEV-NOTE-CLAUDE: Simplified format without end dates for cleaner presentation
        strategy_id_base = f"{strategy_base}_{start_date_str}"

        hash_suffix = hashlib.md5(strategy_id_base.encode()).hexdigest()[:6]
        return f"{strategy_id_base}_{hash_suffix}"
    
    def _calculate_instance_metrics(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate performance metrics for strategy instance.
        """
        if not positions:
            return {}
            
        pnl_column = 'pnl_sol'
        investment_column = 'investment_sol'
        
        financially_valid_positions = [
            pos for pos in positions if pd.notna(pos.get(pnl_column))
        ]
        
        if not financially_valid_positions:
            return { 'total_pnl_sol': 0.0, 'avg_pnl_percent': 0.0, 'win_rate': 0.0, 'position_count': len(positions), 'analyzed_position_count': 0, 'total_invested': 0.0, 'pnl_per_sol_invested': 0.0, 'best_position': 0.0, 'worst_position': 0.0 }
        
        pnl_values = [pos[pnl_column] for pos in financially_valid_positions]
        investment_values = [pos[investment_column] for pos in financially_valid_positions if pd.notna(pos.get(investment_column))]
        
        pnl_percentages = []
        for pos in financially_valid_positions:
            pnl = pos.get(pnl_column)
            investment = pos.get(investment_column)
            if pd.notna(investment) and investment > 0:
                pnl_percentages.append((pnl / investment) * 100)
        
        total_pnl = sum(pnl_values)
        total_invested = sum(investment_values)
        win_count = sum(1 for pnl in pnl_values if pnl > 0)
        win_rate = (win_count / len(pnl_values)) * 100 if pnl_values else 0
        
        return {
            'total_pnl_sol': total_pnl, 'avg_pnl_percent': sum(pnl_percentages) / len(pnl_percentages) if pnl_percentages else 0, 'win_rate': win_rate, 'position_count': len(positions), 'analyzed_position_count': len(financially_valid_positions), 'total_invested': total_invested, 'pnl_per_sol_invested': total_pnl / total_invested if total_invested > 0 else 0, 'best_position': max(pnl_percentages) if pnl_percentages else 0, 'worst_position': min(pnl_percentages) if pnl_percentages else 0
        }
    
    def _calculate_weighted_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate improved weighted performance score for ranking.
        Focus on core business metrics: profitability and consistency.
        Small sample penalty instead of complete exclusion.
        """
        analyzed_count = metrics.get('analyzed_position_count', 0)
        
        # Exclude only completely invalid data
        if analyzed_count == 0:
            return -999
        
        # Core metrics
        avg_pnl = metrics.get('avg_pnl_percent', 0)
        win_rate = metrics.get('win_rate', 0)
        position_count = metrics.get('position_count', 0)
        
        # Small sample penalty (progressive)
        if analyzed_count == 1:
            sample_penalty = -10  # Significant penalty for single position
        elif analyzed_count == 2:
            sample_penalty = -5   # Moderate penalty for two positions
        else:
            sample_penalty = 0    # No penalty for 3+ positions
        
        # Position count bonus (logarithmic scaling for larger samples)
        import math
        if position_count >= 3:
            position_bonus = math.log(position_count) * 1.5
        else:
            position_bonus = 0
        
        # Main scoring formula
        score = (
            avg_pnl * 0.65 +           # 65% - primary profitability metric
            win_rate * 0.30 +          # 30% - consistency metric  
            position_bonus * 0.05      # 5% - statistical reliability bonus
            + sample_penalty           # Penalty for small samples
        )
        
        return score
    
    def _load_merger_config(self) -> Dict[str, Any]:
        """
        Load strategy merger configuration from YAML file.
        
        Returns:
            Dict[str, Any]: Merger configuration or empty dict if file missing/invalid
        """
        config_path = "reporting/config/strategy_merger.yaml"
        
        if not os.path.exists(config_path):
            logger.debug(f"Strategy merger config not found: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'strategy_mergers' not in config:
                logger.warning(f"Invalid strategy merger config structure in {config_path}")
                return {}
                
            logger.info(f"Loaded strategy merger config with {len(config['strategy_mergers'])} groups")
            logger.warning(f"DEBUG: Merger groups loaded: {[g.get('group_name') for g in config['strategy_mergers']]}")
            return config
            
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse strategy merger config: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Error loading strategy merger config: {e}")
            return {}

    def _apply_strategy_merging(self) -> None:
        """
        Apply manual strategy merging based on configuration file.
        
        AIDEV-NOTE-CLAUDE: Integration point - called after PASS 2 but before metrics calculation
        """
        merger_config = self._load_merger_config()
        
        if not merger_config or not merger_config.get('strategy_mergers'):
            logger.debug("No strategy merger configuration found - skipping merging")
            return
        
        total_merged_strategies = 0
        total_moved_positions = 0
        
        for group_config in merger_config['strategy_mergers']:
            group_name = group_config.get('group_name', 'unnamed_group')
            merge_strategies = group_config.get('merge_strategies', [])
            
            if len(merge_strategies) < 2:
                logger.warning(f"Merger group '{group_name}' has fewer than 2 strategies - skipping")
                continue
                
            merged_count, moved_count = self._merge_strategy_instances(group_name, merge_strategies)
            total_merged_strategies += merged_count
            total_moved_positions += moved_count
        
        if total_merged_strategies > 0:
            logger.info(f"Strategy merging completed: {total_merged_strategies} strategies merged, {total_moved_positions} positions moved")
        else:
            logger.debug("No strategies were merged")

    def _merge_strategy_instances(self, group_name: str, merge_strategies: List[str]) -> Tuple[int, int]:
        """
        Merge a group of strategy instances into the oldest one.
        
        Args:
            group_name (str): Name of the merger group for logging
            merge_strategies (List[str]): List of strategy_instance_ids to merge
            
        Returns:
            Tuple[int, int]: (number of strategies merged, number of positions moved)
        """
        # AIDEV-NOTE-CLAUDE: Find existing strategies that match merge list
        existing_strategies = []
        for strategy_id in merge_strategies:
            if strategy_id in self.strategy_instances:
                existing_strategies.append(strategy_id)
            else:
                logger.warning(f"Strategy '{strategy_id}' in group '{group_name}' not found in data - skipping")
        
        if len(existing_strategies) < 2:
            logger.warning(f"Group '{group_name}' has fewer than 2 existing strategies - skipping merge")
            logger.warning(f"DEBUG: Found strategies: {existing_strategies}")
            logger.warning(f"DEBUG: Available strategy IDs: {list(self.strategy_instances.keys())[:5]}...")  # Show first 5
            return 0, 0
        
        # Check for duplicate strategy appearances across groups
        strategies_in_multiple_groups = set()
        for strategy_id in existing_strategies:
            # Simple check - if strategy appears in current merge but was already processed
            # we'll detect this by checking if it has merged_from field
            if 'merged_from' in self.strategy_instances[strategy_id]:
                strategies_in_multiple_groups.add(strategy_id)
        
        if strategies_in_multiple_groups:
            logger.warning(f"Group '{group_name}' contains strategies that appear in multiple merge groups: {strategies_in_multiple_groups} - skipping entire group")
            return 0, 0
        
        # AIDEV-NOTE-CLAUDE: Find oldest strategy by extracting date from strategy_instance_id
        # Format: {strategy}_TP{tp}_SL{sl}_{YYYY-MM-DD}_{hash}
        oldest_strategy_id = None
        oldest_date = None
        
        for strategy_id in existing_strategies:
            try:
                # Extract date part from strategy ID (assumes format with date)
                parts = strategy_id.split('_')
                date_part = None
                for part in parts:
                    if len(part) == 10 and part.count('-') == 2:  # YYYY-MM-DD format
                        date_part = part
                        break
                
                if date_part:
                    strategy_date = datetime.strptime(date_part, '%Y-%m-%d')
                    if oldest_date is None or strategy_date < oldest_date:
                        oldest_date = strategy_date
                        oldest_strategy_id = strategy_id
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse date from strategy ID '{strategy_id}': {e}")
        
        if not oldest_strategy_id:
            logger.warning(f"Could not determine oldest strategy in group '{group_name}' - using first strategy")
            oldest_strategy_id = existing_strategies[0]
        
        # AIDEV-NOTE-CLAUDE: Merge all other strategies into oldest one
        target_strategy = self.strategy_instances[oldest_strategy_id]
        strategies_to_remove = [s for s in existing_strategies if s != oldest_strategy_id]
        
        merged_from_list = [oldest_strategy_id]  # Include the target strategy in merged_from
        moved_positions = 0
        
        for source_strategy_id in strategies_to_remove:
            source_strategy = self.strategy_instances[source_strategy_id]
            
            # Move positions from source to target
            for position in source_strategy['positions']:
                # Update strategy_instance_id in position data
                position['strategy_instance_id'] = oldest_strategy_id
                
                # Add original_strategy_instance_id for audit trail
                position['original_strategy_instance_id'] = source_strategy_id
                
                # Add position to target strategy
                target_strategy['positions'].append(position)
                moved_positions += 1
            
            # Track which strategies were merged
            merged_from_list.append(source_strategy_id)
            
            # Update date range in target strategy
            source_first_date = source_strategy.get('first_use_date')
            source_last_date = source_strategy.get('last_use_date')
            
            if source_first_date and (not target_strategy.get('first_use_date') or source_first_date < target_strategy['first_use_date']):
                target_strategy['first_use_date'] = source_first_date
            
            if source_last_date and (not target_strategy.get('last_use_date') or source_last_date > target_strategy['last_use_date']):
                target_strategy['last_use_date'] = source_last_date
        
        # Add merged_from metadata to target strategy
        target_strategy['merged_from'] = merged_from_list
        
        # Remove merged strategies from strategy_instances
        for strategy_id in strategies_to_remove:
            del self.strategy_instances[strategy_id]
        
        logger.info(f"Merged group '{group_name}': {len(strategies_to_remove)} strategies into '{oldest_strategy_id}', moved {moved_positions} positions")
        
        return len(strategies_to_remove), moved_positions

    def _recalculate_merged_strategy_metrics(self) -> None:
        """
        Recalculate metrics for merged strategies and remove duplicates.
        
        AIDEV-NOTE-CLAUDE: Final step after merging - consolidate statistics and clean up
        """
        strategies_to_remove = set()
        
        for instance_id, instance_data in self.strategy_instances.items():
            merged_from = instance_data.get('merged_from', [])
            
            if len(merged_from) > 1:  # This strategy has merges
                # Collect all positions from merged strategies
                all_positions = []
                all_strategies_data = []
                
                # Collect data from all merged strategies (including representative)
                for merged_strategy_id in merged_from:
                    if merged_strategy_id in self.strategy_instances:
                        strategy_data = self.strategy_instances[merged_strategy_id]
                        all_positions.extend(strategy_data['positions'])
                        all_strategies_data.append(strategy_data)
                        
                        # Mark non-representative strategies for removal
                        if merged_strategy_id != instance_id:
                            strategies_to_remove.add(merged_strategy_id)
                
                if all_positions:
                    # Recalculate metrics for all merged positions
                    new_metrics = self._calculate_instance_metrics(all_positions)
                    
                    # Update strategy metadata with merged data
                    self._update_merged_strategy_metadata(
                        instance_data, all_strategies_data, all_positions, new_metrics
                    )
                    
                    # Update positions list
                    instance_data['positions'] = all_positions
                    instance_data['metrics'] = new_metrics
        
        # Remove merged strategies
        for strategy_id in strategies_to_remove:
            if strategy_id in self.strategy_instances:
                del self.strategy_instances[strategy_id]
                logger.debug(f"Removed merged strategy: {strategy_id}")
        
        # Recalculate weighted scores and rankings for all strategies
        for instance_id, instance_data in self.strategy_instances.items():
            metrics = instance_data.get('metrics', {})
            score = self._calculate_weighted_score(metrics)
            instance_data['weighted_score'] = score
        
        # Update rankings
        sorted_instances = sorted(
            self.strategy_instances.items(), 
            key=lambda x: x[1]['weighted_score'], 
            reverse=True
        )
        for rank, (instance_id, _) in enumerate(sorted_instances, 1):
            self.strategy_instances[instance_id]['rank'] = rank
        
        logger.info(f"Removed {len(strategies_to_remove)} merged strategies and recalculated rankings")

    def _update_merged_strategy_metadata(self, target_strategy: Dict[str, Any], 
                                       all_strategies: List[Dict[str, Any]], 
                                       all_positions: List[Dict[str, Any]], 
                                       new_metrics: Dict[str, float]) -> None:
        """
        Update strategy metadata after merging multiple strategies.
        
        Args:
            target_strategy: Target strategy to update
            all_strategies: List of all merged strategy data
            all_positions: All positions from merged strategies
            new_metrics: Recalculated metrics
        """
        # Find earliest and latest dates
        all_first_dates = [s.get('first_use_date') for s in all_strategies if s.get('first_use_date')]
        all_last_dates = [s.get('last_use_date') for s in all_strategies if s.get('last_use_date')]
        
        if all_first_dates:
            target_strategy['first_use_date'] = min(all_first_dates)
        if all_last_dates:
            target_strategy['last_use_date'] = max(all_last_dates)
        
        # Find strategy with latest date for TP/SL (most recent parameters)
        latest_strategy = max(all_strategies, key=lambda s: s.get('last_use_date', datetime.min))
        latest_params = latest_strategy.get('parameters', {})
        
        # Update parameters with latest TP/SL
        target_strategy['parameters']['takeProfit'] = latest_params.get('takeProfit', 
                                                     target_strategy['parameters'].get('takeProfit'))
        target_strategy['parameters']['stopLoss'] = latest_params.get('stopLoss', 
                                                   target_strategy['parameters'].get('stopLoss'))
        
        # Add merged_from field for all strategies (including non-merged)
        if 'merged_from' not in target_strategy:
            target_strategy['merged_from'] = [target_strategy.get('strategy_instance_id', '')]
        
        logger.debug(f"Updated merged strategy metadata: TP={target_strategy['parameters']['takeProfit']}, "
                    f"SL={target_strategy['parameters']['stopLoss']}, "
                    f"Positions={len(all_positions)}, "
                    f"Date range: {target_strategy['first_use_date']} to {target_strategy['last_use_date']}")
    
    def detect_instances(self, csv_file_path: str) -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
        """Detect strategy instances from positions CSV file with time-gap logic."""
        logger.info(f"Loading positions from {csv_file_path}")
        try:
            df = pd.read_csv(csv_file_path)
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            return pd.DataFrame(), {}
        
        # Backward compatibility for columns
        for col, default in [('wallet_id', 'default_wallet'), ('strategy_instance_id', ''), ('source_file', 'unknown')]:
            if col not in df.columns:
                df[col] = default
        df['strategy_instance_id'] = df['strategy_instance_id'].astype('object')

        # STEP 1: Chronological sort
        from reporting.data_loader import _parse_custom_timestamp
        df['open_timestamp_dt'] = df['open_timestamp'].apply(_parse_custom_timestamp)
        df = df.sort_values(by='open_timestamp_dt').reset_index(drop=True)

        # Maps for session tracking
        last_seen_map: Dict[Tuple[str, float, float], datetime] = {}
        param_to_temp_id_map: Dict[Tuple[str, float, float], str] = {}
        
        # --- PASS 1: Grouping and Temporary IDs ---
        for idx, row in df.iterrows():
            strategy = row.get('strategy_raw', 'unknown')
            tp = row.get('takeProfit', float('nan'))
            sl = row.get('stopLoss', float('nan'))
            
            if pd.isna(row.get('investment_sol')) or row.get('investment_sol') <= 0:
                continue

            param_key = (strategy, tp, sl)
            current_timestamp = row['open_timestamp_dt']
            last_seen_timestamp = last_seen_map.get(param_key)
            
            if last_seen_timestamp is None or (current_timestamp - last_seen_timestamp) > timedelta(days=4):
                # Start new session -> new temporary ID
                temp_id = self._generate_strategy_id(strategy, tp, sl, current_timestamp)
                param_to_temp_id_map[param_key] = temp_id
                
                step_size_match = pd.Series(strategy).str.extract(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', expand=False).iloc[0]
                step_size = step_size_match if pd.notna(step_size_match) else 'UNKNOWN'
                
                self.strategy_instances[temp_id] = {
                    'parameters': { 'strategy': strategy, 'takeProfit': tp, 'stopLoss': sl, 'step_size': step_size },
                    'positions': [],
                    'first_use_date': current_timestamp,
                    'last_use_date': current_timestamp
                }
            else:
                # Continue existing session
                temp_id = param_to_temp_id_map[param_key]
                self.strategy_instances[temp_id]['last_use_date'] = current_timestamp

            df.loc[idx, 'strategy_instance_id'] = temp_id
            self.strategy_instances[temp_id]['positions'].append(row.to_dict())
            last_seen_map[param_key] = current_timestamp

        # --- PASS 2: Finalize IDs ---
        final_instances = {}
        temp_to_final_id_map = {}
        for temp_id, instance_data in self.strategy_instances.items():
            # AIDEV-NOTE-CLAUDE: Simplified ID generation without last_use_date
            final_id = self._generate_strategy_id(
                strategy=instance_data['parameters']['strategy'],
                tp=instance_data['parameters']['takeProfit'],
                sl=instance_data['parameters']['stopLoss'],
                first_use_date=instance_data['first_use_date']
            )
            temp_to_final_id_map[temp_id] = final_id
            final_instances[final_id] = instance_data

        df['strategy_instance_id'] = df['strategy_instance_id'].map(temp_to_final_id_map)
        self.strategy_instances = final_instances
        
        # --- PASS 3: Apply manual merging ---
        self._apply_strategy_merging()
        
        # --- PASS 3B: Recalculate merged strategy metrics ---
        self._recalculate_merged_strategy_metrics()
        
        # Update DataFrame with merged strategy IDs and add original_strategy_instance_id column
        if 'original_strategy_instance_id' not in df.columns:
            df['original_strategy_instance_id'] = df['strategy_instance_id']  # Default: same as current
        
        # Update positions that were moved during merging
        for instance_id, instance_data in self.strategy_instances.items():
            if 'merged_from' in instance_data:
                for position in instance_data['positions']:
                    # Find matching row in DataFrame and update
                    position_mask = (
                        (df['pool_address'] == position.get('pool_address', '')) &
                        (df['open_timestamp'] == position.get('open_timestamp', ''))
                    )
                    
                    if position_mask.any():
                        df.loc[position_mask, 'strategy_instance_id'] = instance_id
                        df.loc[position_mask, 'original_strategy_instance_id'] = position.get('original_strategy_instance_id', instance_id)
        
        # --- PASS 4: Calculate metrics and rankings ---
        # Calculate metrics and rankings
        
        # Calculate metrics and rankings
        for instance_id, instance_data in self.strategy_instances.items():
            metrics = self._calculate_instance_metrics(instance_data['positions'])
            score = self._calculate_weighted_score(metrics)
            instance_data['metrics'] = metrics
            instance_data['weighted_score'] = score
        
        sorted_instances = sorted(self.strategy_instances.items(), key=lambda x: x[1]['weighted_score'], reverse=True)
        for rank, (instance_id, _) in enumerate(sorted_instances, 1):
            self.strategy_instances[instance_id]['rank'] = rank
        
        df = df.drop(columns=['open_timestamp_dt'])
        logger.info(f"Detected {len(self.strategy_instances)} unique strategy instances using time-gap logic.")
        return df, self.strategy_instances
    
    def export_instances_csv(self, output_path: str) -> bool:
        """Export strategy instances to CSV file."""
        if not self.strategy_instances:
            logger.warning("No strategy instances to export")
            return False
        try:
            rows = []
            for instance_id, instance_data in self.strategy_instances.items():
                params = instance_data['parameters']
                metrics = instance_data.get('metrics', {})
                row = {
                    'strategy_instance_id': instance_id,
                    'strategy': params['strategy'], 'step_size': params.get('step_size', 'UNKNOWN'),
                    'investment_sol': pd.Series([p['investment_sol'] for p in instance_data['positions']]).mean(),
                    'takeProfit': params['takeProfit'], 'stopLoss': params['stopLoss'],
                    'first_use_date': instance_data.get('first_use_date').strftime('%Y-%m-%d') if isinstance(instance_data.get('first_use_date'), datetime) else 'unknown',
                    'last_use_date': instance_data.get('last_use_date').strftime('%Y-%m-%d') if isinstance(instance_data.get('last_use_date'), datetime) else 'unknown',
                    'position_count': metrics.get('position_count', 0),
                    'analyzed_position_count': metrics.get('analyzed_position_count', 0),
                    'total_pnl_sol': round(metrics.get('total_pnl_sol', 0), 4),
                    'avg_pnl_percent': round(metrics.get('avg_pnl_percent', 0), 2),
                    'win_rate': round(metrics.get('win_rate', 0), 1),
                    'total_invested': round(metrics.get('total_invested', 0), 4),
                    'pnl_per_sol_invested': round(metrics.get('pnl_per_sol_invested', 0), 4),
                    'best_position': round(metrics.get('best_position', 0), 2),
                    'worst_position': round(metrics.get('worst_position', 0), 2),
                    'weighted_score': round(instance_data.get('weighted_score', 0), 2),
                    'rank': instance_data.get('rank', 0),
                    'merged_from': ','.join(instance_data.get('merged_from', [instance_id]))
                }
                rows.append(row)
            
            rows.sort(key=lambda x: x['rank'])
            df_export = pd.DataFrame(rows)
            df_export.to_csv(output_path, index=False)
            logger.info(f"Exported {len(rows)} strategy instances to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting strategy instances: {e}")
            return False
    
def run_instance_detection(input_csv: str = "positions_to_analyze.csv", output_csv: str = "strategy_instances.csv") -> bool:
    """Run complete strategy instance detection process."""
    logger.info("Starting strategy instance detection...")
    detector = StrategyInstanceDetector()
    updated_df, instances = detector.detect_instances(input_csv)
    
    if updated_df.empty:
        logger.error("Failed to process positions data")
        return False
    
    try:
        updated_df.to_csv(input_csv, index=False)
        logger.info(f"Updated {input_csv} with strategy instance IDs")
    except Exception as e:
        logger.error(f"Error updating positions CSV: {e}")
        return False
    
    success = detector.export_instances_csv(output_csv)
    if success:
        logger.info("Strategy instance detection completed successfully")
        
        # AIDEV-NOTE-CLAUDE: Update positions CSV with merged strategy IDs
        _update_positions_csv_with_merged_strategies(updated_df, input_csv)
        
        top_instances = sorted(instances.items(), key=lambda x: x[1].get('rank', 999))[:3]
        logger.info("Top 3 performing strategies:")
        for instance_id, data in top_instances:
            metrics = data.get('metrics', {})
            logger.info(f"  #{data.get('rank', 0)}: {instance_id} - Avg PnL: {metrics.get('avg_pnl_percent', 0):.1f}%, Win Rate: {metrics.get('win_rate', 0):.1f}%, Positions: {metrics.get('position_count', 0)}")
    return success

def _update_positions_csv_with_merged_strategies(updated_df: pd.DataFrame, csv_file: str) -> None:
    """
    Update positions CSV file with merged strategy instance IDs.
    
    Args:
        updated_df: DataFrame with updated strategy_instance_id values
        csv_file: Path to positions CSV file to update
    """
    try:
        # Read current CSV
        current_df = pd.read_csv(csv_file)
        
        # Add original_strategy_instance_id column if missing
        if 'original_strategy_instance_id' not in current_df.columns:
            current_df['original_strategy_instance_id'] = current_df['strategy_instance_id']
        
        # Create mapping from position identifiers to new strategy IDs
        position_to_strategy_map = {}
        for _, row in updated_df.iterrows():
            # Use pool_address + open_timestamp as universal ID
            position_key = f"{row.get('pool_address', '')}_{row.get('open_timestamp', '')}"
            position_to_strategy_map[position_key] = {
                'new_strategy_id': row.get('strategy_instance_id'),
                'original_strategy_id': row.get('original_strategy_instance_id', row.get('strategy_instance_id'))
            }
        
        # Update CSV rows
        updated_rows = 0
        for idx, row in current_df.iterrows():
            position_key = f"{row.get('pool_address', '')}_{row.get('open_timestamp', '')}"
            if position_key in position_to_strategy_map:
                mapping = position_to_strategy_map[position_key]
                
                # Only update if strategy_instance_id actually changed
                if row['strategy_instance_id'] != mapping['new_strategy_id']:
                    current_df.at[idx, 'original_strategy_instance_id'] = row['strategy_instance_id']
                    current_df.at[idx, 'strategy_instance_id'] = mapping['new_strategy_id']
                    updated_rows += 1
        
        # Write back to CSV if changes were made
        if updated_rows > 0:
            current_df.to_csv(csv_file, index=False)
            logger.info(f"Updated {updated_rows} position records in {csv_file} with merged strategy IDs")
        else:
            logger.debug("No position records needed updating for strategy merging")
            
    except Exception as e:
        logger.error(f"Failed to update positions CSV with merged strategies: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_instance_detection()