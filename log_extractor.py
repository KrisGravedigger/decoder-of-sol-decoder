import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any

# --- Konfiguracja ---
LOG_DIR = "input"
OUTPUT_CSV = "positions_to_analyze.csv"

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('LogExtractor')

# === Klasy Pomocnicze ===

class Position:
    """Przechowuje stan pojedynczej, aktywnej pozycji."""
    def __init__(self, open_timestamp: str, bot_version: str, line_index: int):
        self.open_timestamp = open_timestamp
        self.bot_version = bot_version
        self.open_line_index = line_index
        self.position_id = f"pos_{open_timestamp.replace('/', '-').replace(':', '-')}_{line_index}"
        self.token_pair: Optional[str] = None
        self.pool_address: Optional[str] = None
        self.initial_investment: Optional[float] = None
        self.actual_strategy: str = "UNKNOWN"
        self.close_timestamp: Optional[str] = None
        self.close_reason: Optional[str] = None
        self.final_pnl: Optional[float] = None

    def is_context_complete(self) -> bool:
        return bool(self.token_pair and self.token_pair != "UNKNOWN-SOL")

    def get_validation_errors(self) -> List[str]:
        errors = []
        if not self.pool_address: errors.append("Brak pool_address")
        if not self.initial_investment: errors.append("Brak initial_investment_sol")
        if not self.close_timestamp: errors.append("Brak close_timestamp (pozycja wciąż aktywna)")
        return errors

    def to_csv_row(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id, "token_pair": self.token_pair,
            "pool_address": self.pool_address, "open_timestamp": self.open_timestamp,
            "close_timestamp": self.close_timestamp, "initial_investment_sol": self.initial_investment,
            "final_pnl_sol_from_log": self.final_pnl, "actual_strategy_from_log": self.actual_strategy,
            "close_reason": self.close_reason, "bot_version": self.bot_version,
        }

# === Główna klasa parsująca ===

class LogParser:
    """Zarządza całym procesem parsowania logów."""

    CLOSE_REASONS = {
        "take profit triggered": "TP", "closing position due to high token price increase": "OOR_high_price",
        "price moved above position range": "OOR", "position out of range": "OOR",
        "stop loss triggered": "SL", "successfully closed position": "manual/other",
        "closed position": "manual/other"
    }

    def __init__(self):
        self.all_lines: List[str] = []
        self.active_positions: Dict[str, Position] = {}
        self.finalized_positions: List[Position] = []

    def _clean_ansi(self, text: str) -> str:
        return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

    def _find_context_value(self, patterns: List[str], start_index: int, lookback: int) -> Optional[str]:
        for i in range(start_index, max(-1, start_index - lookback), -1):
            for pattern in patterns:
                match = re.search(pattern, self._clean_ansi(self.all_lines[i]))
                if match: return match.group(1).strip()
        return None

    def _normalize_token_pair(self, text: Optional[str]) -> Optional[str]:
        if not text: return None
        match = re.search(r'([\w\s().-]+-SOL)', self._clean_ansi(text))
        return match.group(1).strip() if match else None

    def _parse_initial_investment(self, start_index: int, lookback: int, lookahead: int) -> Optional[float]:
        # Wersja 5: Agresywne poszukiwanie kwoty inwestycji
        # Okno poszukiwania od momentu otwarcia pozycji
        search_start = start_index
        # Okno może sięgać daleko w przód, bo PnL może być logowany później
        search_end = min(len(self.all_lines), start_index + lookahead)

        for i in range(search_start, search_end):
            line = self._clean_ansi(self.all_lines[i])

            # Wzorzec 1: Najpewniejszy - linia PnL z "Start:"
            # Przykład: PnL: 0.05403 SOL (Return: +0.49%) | Start: 11.10968 SOL → Current: 11.16371 SOL
            if "PnL:" in line and "Start:" in line:
                match = re.search(r'Start:\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Znalaziono kwotę inwestycji '{match.group(1)}' ze wzorca 'PnL+Start' w linii {i+1}")
                    return round(float(match.group(1)), 4)

            # Wzorzec 2: Linia PnL z "Initial"
            # Przykład: Pnl Calculation: ... - Initial 11.10968 SOL
            if "Pnl Calculation:" in line and "Initial" in line:
                match = re.search(r'Initial\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Znalaziono kwotę inwestycji '{match.group(1)}' ze wzorca 'Pnl Calculation+Initial' w linii {i+1}")
                    return round(float(match.group(1)), 4)
            
            # Wzorzec 3: Linia otwierająca pozycję
            if "Creating a position" in line:
                match = re.search(r'with\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Znalaziono kwotę inwestycji '{match.group(1)}' ze wzorca 'Creating+with' w linii {i+1}")
                    return round(float(match.group(1)), 4)

        logger.warning(f"Nie udało się znaleźć kwoty inwestycji dla pozycji otwartej w linii {start_index + 1}")
        return None
        
    def _parse_final_pnl(self, start_index: int, lookback: int) -> Optional[float]:
        for i in range(start_index, max(-1, start_index - lookback), -1):
            line = self._clean_ansi(self.all_lines[i])
            if "PnL:" in line and "Return:" in line:
                match = re.search(r'PnL:\s*(-?\d+\.?\d*)\s*SOL', line)
                if match: return round(float(match.group(1)), 5)
        return None

    def _process_open_event(self, timestamp: str, version: str, index: int):
        # Okno kontekstowe dla otwarcia
        context_start = max(0, index - 50)
        
        token_pair = self._normalize_token_pair(
            self._find_context_value([r'TARGET POOL:\s*(.*-SOL)'], index, 50)
        )
        if not token_pair:
            logger.debug(f"Pominięto otwarcie w linii {index + 1}, brak pary tokenów.")
            return

        pos = Position(timestamp, version, index)
        pos.token_pair = token_pair
        
        pos.pool_address = self._find_context_value([r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', r'dexscreener\.com/solana/([a-zA-Z0-9]+)'], index, 50)
        pos.actual_strategy = self._find_context_value([r'\[(Spot \(1-Sided\)|Bid-Ask \(1-Sided\)|Spot \(Wide\)|Bid-Ask \(Wide\))'], index, 50) or "UNKNOWN"
        
        # NAJWAŻNIEJSZA ZMIANA: Szukaj inwestycji w szerszym oknie W PRZÓD
        pos.initial_investment = self._parse_initial_investment(index, 0, 100)
        
        self.active_positions[pos.position_id] = pos
        logger.info(f"Otwarto pozycję: {pos.position_id} ({pos.token_pair}) | Inv: {pos.initial_investment} | Pool: {pos.pool_address}")

    def _process_close_event(self, timestamp: str, index: int):
        line_lower = self._clean_ansi(self.all_lines[index].lower())
        
        close_reason_code = next((code for text, code in self.CLOSE_REASONS.items() if text in line_lower), None)
        if not close_reason_code: return

        # Zwiększony lookback dla kontekstu zamknięcia do 20 linii
        context_lines_str = " ".join(self.all_lines[max(0, index - 20):index + 1])
        token_pair_in_context = self._normalize_token_pair(context_lines_str)

        if not token_pair_in_context:
            logger.debug(f"Wykryto zamknięcie w linii {index + 1}, ale brak pary w kontekście.")
            return

        matching_position = next((pos for pos_id, pos in reversed(list(self.active_positions.items())) if pos.token_pair == token_pair_in_context), None)
        
        if matching_position:
            pos = matching_position
            pos.close_timestamp = timestamp
            pos.close_reason = close_reason_code
            pos.final_pnl = self._parse_final_pnl(index, 20)
            
            self.finalized_positions.append(pos)
            del self.active_positions[pos.position_id]
            logger.info(f"Zamknięto pozycję: {pos.position_id} ({pos.token_pair}) | Powód: {pos.close_reason} | PnL: {pos.final_pnl}")
        else:
            logger.debug(f"Wykryto zamknięcie dla {token_pair_in_context} w linii {index + 1}, ale brak aktywnej pozycji.")

    def run(self, log_dir: str):
        log_files = sorted([f for f in os.listdir(log_dir) if f.startswith("app") and ".log" in f])
        if not log_files:
            logger.warning(f"Nie znaleziono plików logów w {log_dir}")
            return []

        for f in log_files: self.all_lines.extend(open(os.path.join(log_dir, f), 'r', encoding='utf-8', errors='ignore'))
        logger.info(f"Przetwarzanie {len(self.all_lines)} linii z {len(log_files)} plików logów.")

        for i, line_content in enumerate(self.all_lines):
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', self._clean_ansi(line_content))
            if not timestamp_match: continue
            
            timestamp = timestamp_match.group(1)
            version = re.search(r'(v[\d.]+)', self._clean_ansi(line_content)).group(1) if re.search(r'(v[\d.]+)', self._clean_ansi(line_content)) else "vUNKNOWN"

            if "Creating a position" in line_content: self._process_open_event(timestamp, version, i)
            else: self._process_close_event(timestamp, i)

        for pos_id, pos in self.active_positions.items():
            pos.close_reason = "active_at_log_end"
            self.finalized_positions.append(pos)
            logger.warning(f"Pozycja {pos_id} ({pos.token_pair}) pozostała aktywna na koniec logów.")

        validated_positions = []
        for pos in self.finalized_positions:
            errors = pos.get_validation_errors()
            if not errors:
                validated_positions.append(pos.to_csv_row())
            else:
                logger.warning(f"Odrzucono pozycję {pos.position_id} ({pos.token_pair}). Błędy: {', '.join(errors)}")
        
        logger.info(f"Znaleziono {len(self.finalized_positions)} pozycji. {len(validated_positions)} z nich ma kompletne dane do analizy.")
        return validated_positions

def run_extraction(log_dir=LOG_DIR, output_csv=OUTPUT_CSV):
    logger.info("Rozpoczynanie ekstrakcji danych z logów...")
    os.makedirs(log_dir, exist_ok=True)
    
    parser = LogParser()
    extracted_data = parser.run(log_dir)
    
    if not extracted_data:
        logger.error("Nie udało się wyekstrahować żadnych kompletnych pozycji. Plik CSV nie zostanie utworzony.")
        return False
        
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=extracted_data[0].keys())
            writer.writeheader()
            writer.writerows(extracted_data)
        logger.info(f"Pomyślnie zapisano {len(extracted_data)} pozycji do pliku {output_csv}")
        return True
    except Exception as e:
        logger.error(f"Błąd zapisu do pliku CSV {output_csv}: {e}")
        return False

if __name__ == "__main__":
    run_extraction()