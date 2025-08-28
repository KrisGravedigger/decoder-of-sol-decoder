import pandas as pd
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import hashlib

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
        """Calculate weighted performance score for ranking."""
        weights = { 'avg_pnl_percent': 0.40, 'win_rate': 0.40, 'pnl_per_sol_invested': 0.10, 'best_position': 0.05, 'worst_position': 0.05 }
        normalized_worst = max(0, 100 + metrics.get('worst_position', -100))
        score = ( metrics.get('avg_pnl_percent', 0) * weights['avg_pnl_percent'] + metrics.get('win_rate', 0) * weights['win_rate'] + metrics.get('pnl_per_sol_invested', 0) * 100 * weights['pnl_per_sol_invested'] + metrics.get('best_position', 0) * weights['best_position'] + normalized_worst * weights['worst_position'] )
        return score
    
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
                    'rank': instance_data.get('rank', 0)
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
        top_instances = sorted(instances.items(), key=lambda x: x[1].get('rank', 999))[:3]
        logger.info("Top 3 performing strategies:")
        for instance_id, data in top_instances:
            metrics = data.get('metrics', {})
            logger.info(f"  #{data.get('rank', 0)}: {instance_id} - Avg PnL: {metrics.get('avg_pnl_percent', 0):.1f}%, Win Rate: {metrics.get('win_rate', 0):.1f}%, Positions: {metrics.get('position_count', 0)}")
    return success

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_instance_detection()