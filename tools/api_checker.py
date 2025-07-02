import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- Konfiguracja ---
# Wczytaj klucze API z pliku .env
load_dotenv()
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

# --- Dane Testowe (weźmy problematyczną pozycję titcoin-SOL) ---
TEST_POSITION = {
    "pool_address": "5Dbj3VpZnmDG8WM2G15BWWgoTGwDmPQJuucGSvrffUEk",
    "open_str": "05/12-21:36:49",
    "close_str": "05/12-21:47:04",
    "year": 2025 # Zakładamy rok zgodnie z poprzednimi ustaleniami
}

# --- Funkcje pomocnicze ---

def parse_time(ts_str, year):
    """Prosta funkcja do parsowania daty."""
    return datetime.strptime(f"{year}/{ts_str}", "%Y/%m/%d-%H:%M:%S")

def print_header(title):
    print("\n" + "="*20 + f" {title} " + "="*20)

def test_api_call(name, url, headers, params):
    """Wykonuje i drukuje wynik zapytania API."""
    print(f"--- Test: {name} ---")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        # Spróbuj sparsować jako JSON, jeśli się nie uda, pokaż tekst
        try:
            print(response.json())
        except requests.exceptions.JSONDecodeError:
            print(response.text)
    except Exception as e:
        print(f"WYSTĄPIŁ KRYTYCZNY BŁĄD: {e}")
    print("-"*(42 + len(name)))


# --- Główna funkcja diagnostyczna ---

def main():
    print_header("ROZPOCZYNANIE DIAGNOSTYKI API")
    
    if not MORALIS_API_KEY:
        print("BŁĄD: Brak klucza MORALIS_API_KEY w pliku .env!")
    
    # Przygotuj dane czasowe
    start_dt = parse_time(TEST_POSITION["open_str"], TEST_POSITION["year"])
    end_dt = parse_time(TEST_POSITION["close_str"], TEST_POSITION["year"])
    start_unix = int(start_dt.timestamp())
    end_unix = int(end_dt.timestamp())

    # === TEST 1: MORALIS API (z `fromDate` i `toDate`) ===
    moralis_url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{TEST_POSITION['pool_address']}/ohlcv"
    moralis_headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    moralis_params_date = {
        "timeframe": "10min",
        "fromDate": start_dt.strftime('%Y-%m-%d'),
        "toDate": (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'), # Rozszerzamy datę końca
        "currency": "usd"
    }
    test_api_call("Moralis (by Date)", moralis_url, moralis_headers, moralis_params_date)

    # === TEST 2: MORALIS API (z `from_timestamp` i `to_timestamp`) ===
    moralis_params_unix = {
        "timeframe": "10min",
        "from_timestamp": start_unix,
        "to_timestamp": end_unix,
        "currency": "usd"
    }
    # Uwaga: dokumentacja sugeruje, że ten endpoint może nie wspierać timestampów, ale warto sprawdzić
    # test_api_call("Moralis (by Timestamp)", moralis_url, moralis_headers, moralis_params_unix)
    
    # === TEST 3: BIRDEYE API (darmowe, bez klucza) ===
    birdeye_url = f"https://public-api.birdeye.so/defi/history_price"
    birdeye_params = {
        "address": TEST_POSITION["pool_address"],
        "address_type": "pair",
        "type": "15m",
        "time_from": start_unix,
        "time_to": end_unix
    }
    birdeye_headers = {}
    if BIRDEYE_API_KEY:
        birdeye_headers["X-API-Key"] = BIRDEYE_API_KEY
        
    test_api_call("Birdeye Public API", birdeye_url, birdeye_headers, birdeye_params)
    
    print_header("ZAKOŃCZONO DIAGNOSTYKĘ")


if __name__ == "__main__":
    main()
