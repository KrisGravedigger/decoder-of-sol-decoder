import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- Konfiguracja ---
# Wczytaj klucze API z pliku .env
load_dotenv()
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")

# --- Dane Testowe (PRECYZYJNIE DLA NASZEGO PROBLEMU) ---
# Adres puli "unstable coin-SOL" z data_loader.py
TEST_POOL_ADDRESS = "67C4rdUriP9EFbUo7CeoiFhM52Jgu9LZpe37Jk2k1tHZ"

# Daty, dla których obserwujemy ponowne pobieranie w logach.
# Testujemy DOKŁADNIE te przedziały.
GAPS_TO_TEST = [
    {"start": "2025-08-17", "end": "2025-08-18"}, # Luka z pierwszej problematycznej pozycji
    {"start": "2025-08-23", "end": "2025-08-23"}, # Pojedynczy dzień, który wymaga obejścia API
    {"start": "2025-08-26", "end": "2025-08-26"}, # Kolejny pojedynczy dzień
]

# --- Funkcje pomocnicze ---

def parse_date(date_str):
    """Prosta funkcja do parsowania daty YYYY-MM-DD."""
    return datetime.strptime(date_str, "%Y-%m-%d")

def print_header(title):
    print("\n" + "="*25 + f" {title} " + "="*25)

def test_api_call(name, url, headers, params):
    """Wykonuje i drukuje wynik zapytania API."""
    print(f"\n--- Test: {name} ---")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        
        try:
            response_data = response.json()
            print(response_data)
            if isinstance(response_data, list):
                print(f"==> WYNIK: Otrzymano {len(response_data)} punktów danych.")
            elif isinstance(response_data.get('result'), list):
                 print(f"==> WYNIK: Otrzymano {len(response_data['result'])} punktów danych.")
            elif response_data.get('data', {}).get('items'):
                print(f"==> WYNIK: Otrzymano {len(response_data['data']['items'])} punktów danych.")

        except requests.exceptions.JSONDecodeError:
            print(response.text)
            print(f"==> WYNIK: Odpowiedź nie jest w formacie JSON.")

    except Exception as e:
        print(f"WYSTĄPIŁ KRYTYCZNY BŁĄD: {e}")
    print("-"*(52 + len(name)))


# --- Główna funkcja diagnostyczna ---

def main():
    print_header("ROZPOCZYNANIE PRECYZYJNEJ DIAGNOSTYKI API")
    
    if not MORALIS_API_KEY:
        print("\nBŁĄD: Brak klucza MORALIS_API_KEY w pliku .env! Test Moralis nie powiedzie się.")
        return

    for gap in GAPS_TO_TEST:
        start_str, end_str = gap['start'], gap['end']
        print_header(f"TESTOWANIE LUKI: {start_str} do {end_str}")

        start_dt = parse_date(start_str)
        end_dt = parse_date(end_str)
        
        # --- Test MORALIS API ---
        # Używamy dokładnie tej samej logiki, co w naszym cache managerze
        moralis_url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{TEST_POOL_ADDRESS}/ohlcv"
        moralis_headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
        
        # Obejście problemu Moralis API dla zapytań o jeden dzień
        api_end_dt = end_dt
        if start_dt == end_dt:
            api_end_dt = end_dt + timedelta(days=1)
            print(f"INFO: Stosowanie obejścia Moralis dla pojedynczego dnia (zapytanie o {start_str} do {api_end_dt.strftime('%Y-%m-%d')})")

        moralis_params = {
            "timeframe": "1h", # Używamy 1h dla większej szansy na dane
            "fromDate": start_dt.strftime('%Y-%m-%d'),
            "toDate": api_end_dt.strftime('%Y-%m-%d'),
        }
        test_api_call("Moralis (by Date)", moralis_url, moralis_headers, moralis_params)

        # --- Test BIRDEYE API (jako niezależne źródło do porównania) ---
        start_unix = int(start_dt.timestamp())
        end_unix = int((end_dt + timedelta(days=1) - timedelta(seconds=1)).timestamp()) # Koniec dnia
        
        birdeye_url = "https://public-api.birdeye.so/defi/history_price"
        birdeye_params = {
            "address": TEST_POOL_ADDRESS,
            "address_type": "pair",
            "type": "1H",
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