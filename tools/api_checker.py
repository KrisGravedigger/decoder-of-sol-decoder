import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# --- Konfiguracja ---
# Wczytaj klucze API z pliku .env w głównym katalogu projektu
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")

# --- Dane Testowe (PRECYZYJNIE DLA NASZEGO PROBLEMU) ---
TARGETS_TO_TEST = [
    {
        "name": "SPX6900 (Wormhole)-SOL",
        "pool_address": "2cfmoth8SaKjuSXe7wKcxg5825J8HNKSQQbWAacoUiP6",
        "start": "2025-05-29",  # POPRAWIONY ROK NA BIEŻĄCY
        "end": "2025-05-30"
    },
    {
        "name": "Shark Cat-SOL",
        "pool_address": "ADfGhbkCeT3yrjLCJNY19wJx6VCjxxsJ5LQ8mNWLw6LC",
        "start": "2025-06-13",  # POPRAWIONY ROK NA BIEŻĄCY
        "end": "2025-06-14"
    },
    {
        "name": "GIGACHAD-SOL",
        "pool_address": "44bUbBQxukyZ8rr3B5W8L3Gm8dm1QcL7gERD32zL7vpY",
        "start": "2025-05-29",  # POPRAWIONY ROK NA BIEŻĄCY
        "end": "2025-05-30"
    }
]

# --- Funkcje pomocnicze ---

def parse_date(date_str):
    """Prosta funkcja do parsowania daty YYYY-MM-DD."""
    # POPRAWIONY FORMAT DATY
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
            print(json.dumps(response_data, indent=2))
            
            if isinstance(response_data.get('result'), list):
                 print(f"\n==> WYNIK: Otrzymano {len(response_data['result'])} punktów danych.")
            else:
                print("\n==> WYNIK: Odpowiedź nie zawierała oczekiwanego pola 'result'.")

        except json.JSONDecodeError:
            print(response.text)
            print(f"\n==> WYNIK: Odpowiedź nie jest w formacie JSON.")

    except Exception as e:
        print(f"WYSTĄPIŁ KRYTYCZNY BŁĄD: {e}")
    print("-"*(52 + len(name)))


# --- Główna funkcja diagnostyczna ---

def main():
    print_header("ROZPOCZYNANIE PRECYZYJNEJ DIAGNOSTYKI API V4 (TYLKO MORALIS)")
    
    if not MORALIS_API_KEY:
        print("\nBŁĄD: Brak klucza MORALIS_API_KEY w pliku .env! Upewnij się, że plik .env znajduje się w głównym katalogu projektu.")
        return

    for target in TARGETS_TO_TEST:
        pool_address = target['pool_address']
        start_str, end_str = target['start'], target['end']
        name = target['name']
        print_header(f"TESTOWANIE PARY: {name} ({start_str} do {end_str})")

        start_dt = parse_date(start_str)
        end_dt = parse_date(end_str)
        
        moralis_url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
        moralis_headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
        
        api_end_dt = end_dt
        if start_dt == end_dt:
            api_end_dt = end_dt + timedelta(days=1)
            print(f"INFO: Stosowanie obejścia Moralis dla pojedynczego dnia...")

        moralis_params = {
            "timeframe": "1h",
            "fromDate": start_dt.strftime('%Y-%m-%d'),
            "toDate": api_end_dt.strftime('%Y-%m-%d'),
        }
        test_api_call(f"Moralis dla {name}", moralis_url, moralis_headers, moralis_params)
    
    print_header("ZAKOŃCZONO DIAGNOSTYKĘ V4")


if __name__ == "__main__":
    main()