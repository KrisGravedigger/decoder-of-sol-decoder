import os
import requests
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import logging
from typing import List, Dict, Tuple

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")

# --- Dane Testowe (identyczne jak w api_checker.py) ---
TARGETS_TO_TEST = [
    {
        "name": "SPX6900 (Wormhole)-SOL",
        "pool_address": "2cfmoth8SaKjuSXe7wKcxg5825J8HNKSQQbWAacoUiP6",
        "start": "2025-05-29",
        "end": "2025-05-30"
    },
    {
        "name": "Shark Cat-SOL",
        "pool_address": "ADfGhbkCeT3yrjLCJNY19wJx6VCjxxsJ5LQ8mNWLw6LC",
        "start": "2025-06-13",
        "end": "2025-06-14"
    },
    {
        "name": "GIGACHAD-SOL",
        "pool_address": "44bUbBQxukyZ8rr3B5W8L3Gm8dm1QcL7gERD32zL7vpY",
        "start": "2025-05-29",
        "end": "2025-05-30"
    }
]

# --- Funkcje pomocnicze ---
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")

def print_header(title):
    print("\n" + "="*25 + f" {title} " + "="*25)


# --- WERSJA 1: Obecna, błędna implementacja (skopiowana 1:1) ---
def _fetch_ochlv_from_api_v_old(pool_address: str, start_dt: datetime, end_dt: datetime, timeframe: str) -> Tuple[List[Dict], bool]:
    """ Wierna kopia obecnej, błędnej funkcji. """
    if not MORALIS_API_KEY:
        return [], False

    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    
    from_date_str = start_dt.strftime('%Y-%m-%d')
    to_date_str = end_dt.strftime('%Y-%m-%d')
    
    if from_date_str == to_date_str:
        api_end_dt = end_dt + timedelta(days=1)
        to_date_str = api_end_dt.strftime('%Y-%m-%d')
        logging.info(f"Applying Moralis single-day workaround for {from_date_str}.")

    # BŁĄD: BRAK PARAMETRU 'currency'
    params = {"timeframe": timeframe, "fromDate": from_date_str, "toDate": to_date_str, "limit": 500}
    
    all_results = []
    page_count = 0
    fetch_successful = True
    while True:
        page_count += 1
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            api_result = data.get('result', [])
            if isinstance(api_result, list): all_results.extend(api_result)
            cursor = data.get('cursor')
            if cursor:
                params['cursor'] = cursor
                time.sleep(0.3)
            else:
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"API RequestException for {pool_address}. Error: {e}")
            fetch_successful = False
            break

    processed_data = []
    for point in all_results:
        try:
            processed_data.append({'timestamp': int(datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')).timestamp())})
        except (ValueError, TypeError, KeyError): pass
    
    return processed_data, fetch_successful


# --- WERSJA 2: Proponowana, poprawiona implementacja ---
def _fetch_ochlv_from_api_v_new(pool_address: str, start_dt: datetime, end_dt: datetime, timeframe: str) -> Tuple[List[Dict], bool]:
    """ Poprawiona wersja z dodanym wymaganym parametrem. """
    if not MORALIS_API_KEY:
        return [], False

    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    
    from_date_str = start_dt.strftime('%Y-%m-%d')
    to_date_str = end_dt.strftime('%Y-%m-%d')
    
    if from_date_str == to_date_str:
        api_end_dt = end_dt + timedelta(days=1)
        to_date_str = api_end_dt.strftime('%Y-%m-%d')
        logging.info(f"Applying Moralis single-day workaround for {from_date_str}.")

    # POPRAWKA: DODANO WYMAGANY PARAMETR 'currency'
    params = {"timeframe": timeframe, "fromDate": from_date_str, "toDate": to_date_str, "limit": 500, "currency": "usd"}
    
    all_results = []
    page_count = 0
    fetch_successful = True
    while True:
        page_count += 1
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            api_result = data.get('result', [])
            if isinstance(api_result, list): all_results.extend(api_result)
            cursor = data.get('cursor')
            if cursor:
                params['cursor'] = cursor
                time.sleep(0.3)
            else:
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"API RequestException for {pool_address}. Error: {e}")
            fetch_successful = False
            break

    processed_data = []
    for point in all_results:
        try:
            processed_data.append({'timestamp': int(datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')).timestamp())})
        except (ValueError, TypeError, KeyError): pass
    
    return processed_data, fetch_successful


# --- Główna funkcja testowa ---
def main():
    print_header("Test Porównawczy Metod Pobierania Danych z API")
    
    if not MORALIS_API_KEY:
        print("\nBŁĄD: Brak klucza MORALIS_API_KEY w pliku .env!")
        return

    for target in TARGETS_TO_TEST:
        pool_address = target['pool_address']
        start_dt = parse_date(target['start'])
        end_dt = parse_date(target['end'])
        name = target['name']
        print_header(f"TESTOWANIE PARY: {name}")

        # Test starej metody
        print("--- Uruchamianie WERSJI STAREJ (bez 'currency=usd') ---")
        old_data, old_success = _fetch_ochlv_from_api_v_old(pool_address, start_dt, end_dt, '1h')
        print(f"==> WYNIK (STARA): Pobrano {len(old_data)} punktów danych. Sukces: {old_success}")

        print("\n" + "-"*30 + "\n")
        time.sleep(1) # Mała przerwa między zapytaniami

        # Test nowej metody
        print("--- Uruchamianie WERSJI NOWEJ (z 'currency=usd') ---")
        new_data, new_success = _fetch_ochlv_from_api_v_new(pool_address, start_dt, end_dt, '1h')
        print(f"==> WYNIK (NOWA):  Pobrano {len(new_data)} punktów danych. Sukces: {new_success}")

    print_header("ZAKOŃCZONO TEST PORÓWNAWCZY")

if __name__ == "__main__":
    main()