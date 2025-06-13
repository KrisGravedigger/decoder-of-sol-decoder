import math
from typing import List, Dict, Tuple, Optional

class StrategyAnalyzer:
    """Uruchamia symulacje strategii na podstawie danych historycznych."""
    
    def __init__(self, bin_step: int, num_bins: int = 69):
        self.bin_step = bin_step
        self.num_bins = num_bins
        self.price_factor = 1 + self.bin_step / 10000

    def _calculate_spot_distribution(self, initial_sol: float) -> List[float]:
        """Równomierny rozkład płynności."""
        return [initial_sol / self.num_bins] * self.num_bins

    def _calculate_bidask_distribution(self, initial_sol: float) -> List[float]:
        """Progresywny rozkład płynności (więcej na krańcach)."""
        weights = [math.exp((i - self.num_bins / 2)**2 / (2 * (self.num_bins / 3)**2)) for i in range(self.num_bins)]
        total_weight = sum(weights)
        return [initial_sol * w / total_weight for w in weights]

    def _get_active_bin_from_price_ratio(self, price_ratio: float) -> int:
        """Oblicza, który bin jest aktywny na podstawie zmiany ceny."""
        if price_ratio <= 1:
            return 0
        active_bin = math.floor(math.log(price_ratio) / math.log(self.price_factor))
        return min(active_bin, self.num_bins - 1)

    def run_all_simulations(self, position_data: Dict, price_history: List[Dict]) -> Dict:
        """Uruchamia 4 symulacje dla danej pozycji i historii cen."""
        if not price_history:
            return {"error": "Brak historii cen do symulacji."}

        initial_sol = position_data['initial_investment_sol']
        initial_price = price_history[0]['close']
        final_price = price_history[-1]['close']
        price_ratio = final_price / initial_price

        # Estymacja opłat na podstawie rzeczywistego PnL i IL
        # PnL_rzeczywisty = PnL_z_opłat + PnL_ze_zmiany_ceny (IL)
        # Dla 1-Sided, IL jest zerowy gdy cena spada, a gdy rośnie, jest to koszt alternatywny
        # (trzymaliśmy SOL zamiast tokena, który zyskał na wartości).
        # Dla uproszczenia, zakładamy, że PnL ze zmiany ceny dla 1-sided to 0.
        # Wtedy cały zysk/strata (poza SL/TP) to opłaty. To uproszczenie, ale wystarczające do porównania.
        # W Twoim przypadku rzeczywista strategia była 1-Sided, więc:
        actual_pnl_from_log = position_data.get('final_pnl_sol_from_log')
        # Jeśli nie ma PnL, załóżmy 0.5% opłat od inwestycji jako baseline
        estimated_total_fees = actual_pnl_from_log if actual_pnl_from_log is not None else initial_sol * 0.005

        results = {}
        spot_dist = self._calculate_spot_distribution(initial_sol)
        bidask_dist = self._calculate_bidask_distribution(initial_sol)

        # Symulacje
        results['Spot (1-Sided)'] = self._simulate_1sided(spot_dist, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees)
        results['Bid-Ask (1-Sided)'] = self._simulate_1sided(bidask_dist, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees)
        results['Spot (Wide)'] = self._simulate_wide(spot_dist, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees)
        results['Bid-Ask (Wide)'] = self._simulate_wide(bidask_dist, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees)
        
        return results

    def _simulate_1sided(self, distribution: List[float], price_ratio: float, initial_price: float, final_price: float, initial_sol: float, fee_budget: float) -> Dict:
        """Symuluje wejście 1-Sided (tylko SOL)."""
        active_bin_index = self._get_active_bin_from_price_ratio(price_ratio)
        
        # PnL ze zmiany wartości aktywów (IL)
        # Sprzedajemy SOL za tokeny, gdy cena rośnie
        sol_converted = sum(distribution[:active_bin_index])
        
        # Uśredniona cena zakupu tokenów
        tokens_bought = 0
        if sol_converted > 0:
            for i in range(active_bin_index):
                bin_price = initial_price * (self.price_factor ** (i + 0.5))
                tokens_bought += distribution[i] / bin_price
        
        remaining_sol = initial_sol - sol_converted
        final_value_of_assets = (tokens_bought * final_price) + remaining_sol
        pnl_from_assets = final_value_of_assets - initial_sol

        # PnL z opłat
        # Opłaty są proporcjonalne do płynności w aktywnym binie
        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[active_bin_index]
        # Unikaj dzielenia przez zero, jeśli spot_liquidity_per_bin jest 0
        liquidity_ratio = active_bin_liquidity / spot_liquidity_per_bin if spot_liquidity_per_bin > 0 else 1.0
        
        pnl_from_fees = fee_budget * liquidity_ratio
        
        total_pnl = pnl_from_assets + pnl_from_fees
        
        return {
            'pnl_sol': total_pnl,
            'return_pct': (total_pnl / initial_sol) * 100,
            'pnl_from_fees': pnl_from_fees,
            'pnl_from_il': pnl_from_assets,
            'activated_bins': active_bin_index
        }

    def _simulate_wide(self, distribution: List[float], price_ratio: float, initial_price: float, final_price: float, initial_sol: float, fee_budget: float) -> Dict:
        """Symuluje wejście Wide (50/50 wartościowo na starcie)."""
        center_bin_index = self.num_bins // 2
        
        # Początkowy stan: połowa wartości w SOL, połowa w tokenach
        initial_sol_half = initial_sol / 2
        initial_tokens_value = initial_sol / 2
        initial_tokens = initial_tokens_value / initial_price
        
        # Wartość HODL (trzymania 50/50 bez LP)
        hodl_value = (initial_tokens * final_price) + initial_sol_half
        
        # Wartość w LP (z uwzględnieniem IL)
        lp_value = 2 * math.sqrt(initial_tokens * final_price * initial_sol_half) # Uproszczony wzór na wartość LP
        
        pnl_from_assets = lp_value - initial_sol

        # PnL z opłat
        # Opłaty są proporcjonalne do płynności w aktywnym binie
        active_bin_index = center_bin_index + self._get_active_bin_from_price_ratio(price_ratio) - (self.num_bins//2 if price_ratio < 1 else 0)
        active_bin_index = max(0, min(active_bin_index, self.num_bins - 1))

        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[active_bin_index]
        liquidity_ratio = active_bin_liquidity / spot_liquidity_per_bin if spot_liquidity_per_bin > 0 else 1.0
        
        pnl_from_fees = fee_budget * liquidity_ratio
        
        total_pnl = pnl_from_assets + pnl_from_fees

        return {
            'pnl_sol': total_pnl,
            'return_pct': (total_pnl / initial_sol) * 100,
            'pnl_from_fees': pnl_from_fees,
            'pnl_from_il': pnl_from_assets,
        }