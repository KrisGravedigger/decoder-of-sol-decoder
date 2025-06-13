import os
import csv
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import shutil
from typing import Dict, List, Optional, Any # Dodano brakujący import

# Importy z naszych modułów
import log_extractor
from strategy_analyzer import StrategyAnalyzer

# --- Konfiguracja ---
LOG_DIR = "input"
POSITIONS_CSV = "positions_to_analyze.csv"
FINAL_REPORT_CSV = "final_analysis_report.csv"
DETAILED_REPORTS_DIR = "detailed_reports"
PRICE_CACHE_DIR = "price_cache"

# Wczytywanie zmiennych środowiskowych z pliku .env
load_dotenv()
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MainAnalyzer')

def parse_timestamp_str(ts_str: str) -> Optional[datetime]:
    if not isinstance(ts_str, str): return None
    try:
        if "-24:" in ts_str:
            logger.warning(f"Wykryto nieprawidłową godzinę '24' w '{ts_str}'. Zmieniam na '23:59:59'.")
            date_part, time_part = ts_str.split('-')
            h, m, s = time_part.split(':')
            if h == '24': ts_str = f"{date_part}-23:59:59"
        
        return datetime.strptime(f"2025/{ts_str}", "%Y/%m/%d-%H:%M:%S")
    except (ValueError, TypeError) as e:
        logger.error(f"Błąd parsowania daty '{ts_str}': {e}")
        return None

def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    """
    Wersja 6: Poprawiony wybór timeframe i odporne parsowanie odpowiedzi API.
    """
    os.makedirs(PRICE_CACHE_DIR, exist_ok=True)
    
    start_unix = int(start_dt.timestamp())
    end_unix = int(end_dt.timestamp())
    cache_file = os.path.join(PRICE_CACHE_DIR, f"{pool_address}_{start_unix}_{end_unix}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Wczytuję ceny z cache dla {pool_address}")
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Błąd pliku cache, pobieram dane z API.")

    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    
    # --- KLUCZOWA ZMIANA: Poprawiony wybór timeframe ---
    if duration_hours <= 4: timeframe = "10min"  # Zamiast 15min
    elif duration_hours <= 12: timeframe = "30min"
    elif duration_hours <= 72: timeframe = "1h"
    else: timeframe = "4h"
    # ----------------------------------------------------

    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    
    start_date_str = start_dt.strftime('%Y-%m-%d')
    end_date_str = end_dt.strftime('%Y-%m-%d')

    if start_date_str >= end_date_str:
        end_date_extended = end_dt + timedelta(days=1)
        end_date_str = end_date_extended.strftime('%Y-%m-%d')
        logger.debug(f"Rozszerzono 'toDate' do: {end_date_str}")
    
    params = {"timeframe": timeframe, "fromDate": start_date_str, "toDate": end_date_str, "currency": "usd"}
    
    try:
        logger.info(f"Pobieram ceny dla {pool_address} (parametry API: {params})...")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        processed_data = []
        api_result = data.get('result', []) if isinstance(data, dict) else data
        
        # --- ZMIANA: Odporne parsowanie odpowiedzi ---
        if isinstance(api_result, list):
            for d in api_result:
                if isinstance(d, dict) and 'close' in d:
                    # Sprawdź, czy istnieje klucz 'time' lub 'timestamp'
                    ts_val = d.get('time') or d.get('timestamp')
                    if ts_val:
                        # 'time' jest w milisekundach, 'timestamp' może być w ISO 8601
                        ts = 0
                        if isinstance(ts_val, (int, float, str)) and str(ts_val).isdigit():
                            ts = int(ts_val) // 1000
                        elif isinstance(ts_val, str):
                            try:
                                ts_dt = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                ts = int(ts_dt.timestamp())
                            except ValueError:
                                logger.warning(f"Nie udało się sparsować stringu z datą: {ts_val}")
                                continue
                        else:
                            continue

                        if start_unix <= ts <= end_unix:
                            processed_data.append({'timestamp': ts, 'close': float(d['close'])})
                    else:
                        logger.warning(f"Otrzymano świeczkę bez klucza 'time' lub 'timestamp': {d}")
                else:
                    logger.warning(f"Otrzymano nieprawidłowy format świeczki od API: {d}")
            processed_data.sort(key=lambda x: x['timestamp'])
        # -------------------------------------------

        with open(cache_file, 'w') as f: json.dump(processed_data, f)
            
        return processed_data
    except requests.exceptions.HTTPError as e:
        logger.error(f"Błąd HTTP {e.response.status_code} dla {pool_address}: {e.response.text}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd sieci dla {pool_address}: {e}")
        return []

def generate_text_report(position_data: Dict, sim_results: Dict) -> str:
    report = []
    report.append("="*60)
    report.append(f"ANALIZA POZYCJI: {position_data['token_pair']}")
    report.append(f"Pool: {position_data['pool_address']}")
    report.append(f"Okres: {position_data['open_timestamp']} -> {position_data['close_timestamp']}")
    report.append("="*60)
    
    report.append(f"\n--- DANE WEJŚCIOWE ---")
    initial_inv = position_data.get('initial_investment_sol', 0)
    report.append(f"Inwestycja: {initial_inv:.4f} SOL")
    report.append(f"Rzeczywista strategia: {position_data.get('actual_strategy_from_log', 'N/A')}")
    final_pnl_log = position_data.get('final_pnl_sol_from_log')
    report.append(f"Rzeczywisty PnL (z logu): {final_pnl_log if final_pnl_log is not None else 'N/A'}")

    report.append(f"\n--- WYNIKI SYMULACJI (PnL w SOL) ---")
    
    if not sim_results or 'error' in sim_results:
        report.append("Błąd podczas symulacji lub brak wyników.")
    else:
        sorted_results = sorted(sim_results.items(), key=lambda item: item[1].get('pnl_sol', -9e9), reverse=True)
        for name, res in sorted_results:
            pnl = res.get('pnl_sol', 0)
            fees = res.get('pnl_from_fees', 0)
            il = res.get('pnl_from_il', 0)
            report.append(f"\n- Strategia: {name}")
            report.append(f"  > Całkowity PnL: {pnl:+.5f} SOL ({res.get('return_pct', 0):.2f}%)")
            report.append(f"    (Szac. opłaty: {fees:+.5f} | Szac. zmiana wartości/IL: {il:+.5f})")

        report.append("\n" + "="*60)
        report.append(f"NAJLEPSZA STRATEGIA: {sorted_results[0][0]}")
        report.append("="*60)
    
    return "\n".join(report)

def main():
    if not MORALIS_API_KEY:
        logger.error("Brak klucza MORALIS_API_KEY w pliku .env! Przerwanie analizy.")
        return

    if os.path.exists(PRICE_CACHE_DIR):
        logger.info(f"Czyszczenie starego cache'u z folderu: {PRICE_CACHE_DIR}")
        shutil.rmtree(PRICE_CACHE_DIR)
    
    logger.info("Krok 1: Uruchamianie ekstraktora logów...")
    if not log_extractor.run_extraction(log_dir=LOG_DIR, output_csv=POSITIONS_CSV):
        logger.error("Ekstrakcja logów nie powiodła się. Analiza przerwana.")
        return
        
    logger.info(f"\nKrok 2: Wczytywanie pozycji z pliku {POSITIONS_CSV}")
    try:
        positions_df = pd.read_csv(POSITIONS_CSV)
        logger.info(f"Wczytano {len(positions_df)} pozycji do analizy.")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        logger.error(f"Plik {POSITIONS_CSV} nie został znaleziony lub jest pusty. Przerwano.")
        return

    logger.info("\nKrok 3: Rozpoczynanie analizy i symulacji...")
    os.makedirs(DETAILED_REPORTS_DIR, exist_ok=True)
    all_final_results = []
    
    analyzer = StrategyAnalyzer(bin_step=100) 

    for index, position in positions_df.iterrows():
        logger.info(f"\n--- Analizuję pozycję {index+1}/{len(positions_df)}: {position['token_pair']} ---")
        position_dict = position.to_dict()

        start_dt = parse_timestamp_str(position['open_timestamp'])
        end_dt = parse_timestamp_str(position['close_timestamp'])

        if not start_dt or not end_dt or start_dt >= end_dt:
            logger.warning(f"Pominięto pozycję {position['position_id']} z powodu nieprawidłowych dat.")
            continue
            
        price_history = fetch_price_history(position['pool_address'], start_dt, end_dt)
        time.sleep(0.6)
        
        if not price_history:
            logger.warning(f"Brak historii cen dla {position['token_pair']}. Pomijam symulację.")
            continue
            
        simulation_results = analyzer.run_all_simulations(position_dict, price_history)
        
        text_report = generate_text_report(position_dict, simulation_results)
        report_filename = os.path.join(DETAILED_REPORTS_DIR, f"{position['token_pair'].replace('/', '_')}_{position['open_timestamp'].replace('/','-').replace(':','-')}.txt")
        with open(report_filename, 'w', encoding='utf-8') as f: f.write(text_report)
        logger.info(f"Zapisano szczegółowy raport: {report_filename}")
        
        best_strategy_name = "error"
        best_pnl = None
        if simulation_results and 'error' not in simulation_results:
            best_strategy_name = max(simulation_results, key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            best_pnl = simulation_results[best_strategy_name].get('pnl_sol')

        final_row = { **position_dict, "best_sim_strategy": best_strategy_name, "best_sim_pnl": best_pnl }
        if simulation_results and 'error' not in simulation_results:
            for name, res in simulation_results.items():
                final_row[f"pnl_{name.replace(' ','_').lower()}"] = res.get('pnl_sol')
        
        all_final_results.append(final_row)

    logger.info(f"\nKrok 4: Zapisywanie końcowego raportu zbiorczego...")
    if all_final_results:
        final_df = pd.DataFrame(all_final_results)
        cols = list(final_df.columns)
        preferred_order = ["position_id", "token_pair", "pool_address", "open_timestamp", "close_timestamp", 
                           "initial_investment_sol", "final_pnl_sol_from_log", "best_sim_strategy", "best_sim_pnl"]
        ordered_cols = preferred_order + [c for c in cols if c not in preferred_order]
        final_df = final_df[ordered_cols]
        final_df.to_csv(FINAL_REPORT_CSV, index=False, encoding='utf-8')
        logger.info(f"Zapisano raport końcowy do: {FINAL_REPORT_CSV}")
    else:
        logger.warning("Nie wygenerowano żadnych wyników końcowych.")
        
    logger.info("\nAnaliza zakończona pomyślnie!")

if __name__ == "__main__":
    main()