import pandas as pd
import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime
import hashlib

# AIDEV-NOTE-CLAUDE: Core module for grouping positions into strategy instances
# Business logic: group by strategy+tp+sl+investment(±0.005 tolerance)

logger = logging.getLogger('StrategyInstanceDetector')

class StrategyInstanceDetector:
    """
    Detects and groups positions into strategy instances based on parameters.
    
    Strategy instance = unique combination of:
    - strategy (exact match)
    - takeProfit (exact match) 
    - stopLoss (exact match)
    - initial_investment (±0.005 SOL tolerance)
    """
    
    def __init__(self, investment_tolerance: float = 0.005):
        """
        Initialize detector with configuration.
        
        Args:
            investment_tolerance (float): Tolerance for investment amount grouping (default: 0.005 SOL)
        """
        self.investment_tolerance = investment_tolerance
        self.strategy_instances: Dict[str, Dict[str, Any]] = {}
        self.position_to_instance: Dict[str, str] = {}
        
    def _generate_strategy_id(self, strategy: str, tp: float, sl: float, investment: float) -> str:
        """
        Generate unique strategy instance ID.
        
        Args:
            strategy: Strategy name (spot, bidask, etc.)
            tp: Take profit percentage
            sl: Stop loss percentage  
            investment: Investment amount (normalized)

        Format: {strategy}_{investment_rounded}_{tp_formatted}_{sl_formatted}_{hash6}
            - investment_rounded: rounded to 3 decimal places
            - tp_formatted/sl_formatted: int if whole number, otherwise 1 decimal place  
            - hash6: first 6 characters of MD5 hash for uniqueness
            
        Returns:
            Unique strategy instance ID
        """
        # AIDEV-NOTE-CLAUDE: Consistent formatting to avoid float precision issues
        # AIDEV-NOTE-GEMINI: Added NaN check to prevent crashes.
        investment_rounded = round(investment, 3)
        
        # Handle potential NaN values for tp and sl
        if pd.isna(tp):
            tp_formatted = 'NaN'
        else:
            tp_formatted = int(tp) if tp == int(tp) else round(tp, 1)

        if pd.isna(sl):
            sl_formatted = 'NaN'
        else:
            sl_formatted = int(sl) if sl == int(sl) else round(sl, 1)
        
        # Create readable ID: strategy_investment_tp_sl
        strategy_id = f"{strategy}_{investment_rounded}_{tp_formatted}_{sl_formatted}"
        
        # Add hash suffix to ensure uniqueness in edge cases
        hash_input = f"{strategy}_{investment_rounded}_{tp_formatted}_{sl_formatted}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        return f"{strategy_id}_{hash_suffix}"
    
    def _find_matching_instance(self, strategy: str, tp: float, sl: float, investment: float) -> str:
        """
        Find existing strategy instance that matches parameters within tolerance.
        
        Args:
            strategy: Strategy name
            tp: Take profit percentage
            sl: Stop loss percentage
            investment: Investment amount
            
        Returns:
            Strategy instance ID if match found, None otherwise
        """
        for instance_id, instance_data in self.strategy_instances.items():
            params = instance_data['parameters']
            
            # Exact match for strategy, tp, sl
            if (params['strategy'] == strategy and 
                params['takeProfit'] == tp and 
                params['stopLoss'] == sl):
                
                # Investment within tolerance
                investment_diff = abs(params['initial_investment'] - investment)
                if investment_diff <= self.investment_tolerance:
                    return instance_id
                    
        return None
    
    def _calculate_instance_metrics(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate performance metrics for strategy instance.
        
        Args:
            positions: List of all positions belonging to this instance
            
        Returns:
            Dictionary with calculated metrics. Returns zeroed metrics if no
            financially valid positions are found.
        """
        if not positions:
            return {}
            
        pnl_column = 'pnl_sol'
        investment_column = 'investment_sol'
        
        # Krok 1: Rygorystyczne filtrowanie pozycji z poprawnym PnL
        financially_valid_positions = [
            pos for pos in positions if pd.notna(pos.get(pnl_column))
        ]
        
        # Krok 2: Obsługa braku ważnych pozycji
        if not financially_valid_positions:
            return {
                'total_pnl_sol': 0.0,
                'avg_pnl_percent': 0.0,
                'win_rate': 0.0,
                'position_count': len(positions),
                'analyzed_position_count': 0, # Nowa metryka
                'total_invested': 0.0,
                'pnl_per_sol_invested': 0.0,
                'best_position': 0.0,
                'worst_position': 0.0
            }
        
        # Krok 3: Obliczenia na podstawie przefiltrowanych danych
        pnl_values = [pos[pnl_column] for pos in financially_valid_positions]
        investment_values = [pos[investment_column] for pos in financially_valid_positions if pd.notna(pos.get(investment_column))]
        
        # Obliczanie procentowego zwrotu tylko dla ważnych pozycji
        pnl_percentages = []
        for pos in financially_valid_positions:
            pnl = pos.get(pnl_column)
            investment = pos.get(investment_column)
            if pd.notna(investment) and investment > 0:
                pnl_percent = (pnl / investment) * 100
                pnl_percentages.append(pnl_percent)
        
        total_pnl = sum(pnl_values)
        total_invested = sum(investment_values)
        win_count = sum(1 for pnl in pnl_values if pnl > 0)
        win_rate = (win_count / len(pnl_values)) * 100
        
        metrics = {
            'total_pnl_sol': total_pnl,
            'avg_pnl_percent': sum(pnl_percentages) / len(pnl_percentages) if pnl_percentages else 0,
            'win_rate': win_rate,
            'position_count': len(positions), # Całkowita liczba pozycji
            'analyzed_position_count': len(financially_valid_positions), # Liczba przeanalizowanych
            'total_invested': total_invested,
            'pnl_per_sol_invested': total_pnl / total_invested if total_invested > 0 else 0,
            'best_position': max(pnl_percentages) if pnl_percentages else 0,
            'worst_position': min(pnl_percentages) if pnl_percentages else 0
        }
        
        return metrics
    
    def _calculate_weighted_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate weighted performance score for ranking.
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Weighted score (higher = better performance)
        """
        # AIDEV-NOTE-CLAUDE: Weights as specified: avg_pnl_percent=0.4, win_rate=0.4, 
        # pnl_per_sol_invested=0.1, best_position=0.05, worst_position=0.05
        
        weights = {
            'avg_pnl_percent': 0.40,
            'win_rate': 0.40, 
            'pnl_per_sol_invested': 0.10,
            'best_position': 0.05,
            'worst_position': 0.05  # Note: this is positive contribution (less negative = better)
        }
        
        # Normalize worst_position (convert negative losses to positive score)
        # If worst_position is -10%, we want this to contribute positively when it's closer to 0
        normalized_worst = max(0, 100 + metrics.get('worst_position', -100))  # -10% becomes 90 points
        
        score = (
            metrics.get('avg_pnl_percent', 0) * weights['avg_pnl_percent'] +
            metrics.get('win_rate', 0) * weights['win_rate'] +
            metrics.get('pnl_per_sol_invested', 0) * 100 * weights['pnl_per_sol_invested'] +  # Convert to percentage scale
            metrics.get('best_position', 0) * weights['best_position'] +
            normalized_worst * weights['worst_position']
        )
        
        return score
    
    def detect_instances(self, csv_file_path: str) -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
        """
        Detect strategy instances from positions CSV file.
        
        Args:
            csv_file_path: Path to positions CSV file
            
        Returns:
            Tuple of (updated_dataframe, strategy_instances_dict)
        """
        logger.info(f"Loading positions from {csv_file_path}")
        
        # Load CSV with column name-based access (future-proof)
        try:
            df = pd.read_csv(csv_file_path)
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            return pd.DataFrame(), {}
        
        # Add new columns if they don't exist (backward compatibility)
        if 'wallet_id' not in df.columns:
            df['wallet_id'] = 'default_wallet'
            logger.info("Added default wallet_id for backward compatibility")
            
        if 'strategy_instance_id' not in df.columns:
            df['strategy_instance_id'] = ''
            # Ensure column is object dtype to accept strings
            df['strategy_instance_id'] = df['strategy_instance_id'].astype('object')
            
        if 'source_file' not in df.columns:
            df['source_file'] = 'unknown'
        
        logger.info(f"Processing {len(df)} positions")
        
        # Group positions into strategy instances
        for idx, row in df.iterrows():
            # AIDEV-NOTE-CLAUDE: Column name mapping for compatibility with CSV from log_extractor
            column_mapping = {
                'strategy': 'strategy_raw',  # Runtime column name
                'investment': 'investment_sol',   # Runtime column name  
                'final_pnl': 'pnl_sol'    # Runtime column name
            }

            # Extract required parameters with proper column names
            strategy = row.get(column_mapping['strategy'], 'unknown')
            tp = row.get('takeProfit', float('nan'))  # This should match CSV exactly
            sl = row.get('stopLoss', float('nan'))    # This should match CSV exactly  
            investment = row.get(column_mapping['investment'], 0)
            
            # Skip rows with missing critical data
            if pd.isna(investment) or investment <= 0:
                logger.warning(f"Skipping position {row.get('position_id', 'unknown')} - invalid investment amount: {investment}")
                continue
                           
            # Find or create strategy instance
            instance_id = self._find_matching_instance(strategy, tp, sl, investment)
            
            if instance_id is None:
                # Create new instance
                instance_id = self._generate_strategy_id(strategy, tp, sl, investment)
                
                # AIDEV-NOTE-GEMINI: CRITICAL FIX - Extract and store step_size.
                step_size_match = pd.Series(strategy).str.extract(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', expand=False).iloc[0]
                step_size = step_size_match if pd.notna(step_size_match) else 'UNKNOWN'

                self.strategy_instances[instance_id] = {
                    'parameters': {
                        'strategy': strategy,
                        'takeProfit': tp,
                        'stopLoss': sl,
                        'initial_investment': investment,
                        'step_size': step_size # Add the extracted step_size
                    },
                    'positions': [],
                    'first_use_date': row.get('open_timestamp', 'unknown')
                }
                
                logger.debug(f"Created new strategy instance: {instance_id}")
            
            # Add position to instance
            position_data = row.to_dict()
            self.strategy_instances[instance_id]['positions'].append(position_data)
            
            # Update dataframe with instance ID  
            df.loc[idx, 'strategy_instance_id'] = instance_id
            self.position_to_instance[row.get('position_id', idx)] = instance_id
        
        # Calculate metrics and rankings for all instances  
        instance_scores = []
        
        for instance_id, instance_data in self.strategy_instances.items():
            metrics = self._calculate_instance_metrics(instance_data['positions'])
            score = self._calculate_weighted_score(metrics)
            
            instance_data['metrics'] = metrics
            instance_data['weighted_score'] = score
            instance_scores.append((instance_id, score))
        
        # Sort by score (highest first) and assign ranks
        instance_scores.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (instance_id, score) in enumerate(instance_scores, 1):
            self.strategy_instances[instance_id]['rank'] = rank
        
        logger.info(f"Detected {len(self.strategy_instances)} unique strategy instances")
        
        return df, self.strategy_instances
    
    def export_instances_csv(self, output_path: str) -> bool:
        """
        Export strategy instances to CSV file.
        
        Args:
            output_path: Path for output CSV file
            
        Returns:
            True if export successful, False otherwise
        """
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
                    'strategy': params['strategy'],
                    'step_size': params.get('step_size', 'UNKNOWN'),
                    'investment_sol': params['initial_investment'],
                    'takeProfit': params['takeProfit'],
                    'stopLoss': params['stopLoss'],
                    'first_use_date': instance_data.get('first_use_date', 'unknown'),
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
            
            # Sort by rank for output
            rows.sort(key=lambda x: x['rank'])
            
            df_export = pd.DataFrame(rows)
            df_export.to_csv(output_path, index=False)
            
            logger.info(f"Exported {len(rows)} strategy instances to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting strategy instances: {e}")
            return False


def run_instance_detection(input_csv: str = "positions_to_analyze.csv", 
                          output_csv: str = "strategy_instances.csv",
                          investment_tolerance: float = 0.005) -> bool:
    """
    Run complete strategy instance detection process.
    
    Args:
        input_csv: Input positions CSV file path
        output_csv: Output strategy instances CSV file path  
        investment_tolerance: Investment amount tolerance for grouping
        
    Returns:
        True if process completed successfully, False otherwise
    """
    logger.info("Starting strategy instance detection...")
    
    detector = StrategyInstanceDetector(investment_tolerance=investment_tolerance)
    
    # Detect instances and update positions CSV
    updated_df, instances = detector.detect_instances(input_csv)
    
    if updated_df.empty:
        logger.error("Failed to process positions data")
        return False
    
    # Save updated positions CSV with strategy_instance_id
    try:
        updated_df.to_csv(input_csv, index=False)
        logger.info(f"Updated {input_csv} with strategy instance IDs")
    except Exception as e:
        logger.error(f"Error updating positions CSV: {e}")
        return False
    
    # Export strategy instances summary
    success = detector.export_instances_csv(output_csv)
    
    if success:
        logger.info("Strategy instance detection completed successfully")
        logger.info(f"Found {len(instances)} unique strategy instances")
        
        # Log top 3 strategies
        top_instances = sorted(instances.items(), key=lambda x: x[1].get('rank', 999))[:3]
        logger.info("Top 3 performing strategies:")
        for instance_id, data in top_instances:
            metrics = data.get('metrics', {})
            logger.info(f"  #{data.get('rank', 0)}: {instance_id} - "
                       f"Avg PnL: {metrics.get('avg_pnl_percent', 0):.1f}%, "
                       f"Win Rate: {metrics.get('win_rate', 0):.1f}%, "
                       f"Positions: {metrics.get('position_count', 0)}")
    
    return success


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run instance detection
    run_instance_detection()