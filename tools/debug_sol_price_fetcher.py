import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import json

# --- Setup ---
load_dotenv()
API_KEY = os.getenv("MORALIS_API_KEY")

# AIDEV-NOTE-GEMINI: Using the pair address for a major USDC/SOL pool (from Raydium), as this is what the /pairs/ endpoint expects.
# This address is known to be a high-liquidity source.
# Previous attempt with native SOL address was incorrect for this endpoint.
PAIR_ADDRESS = "83v8iPyZihDEjDdY8RdZddyZNyUtXngz69Lgo9Kt5d6d" 

# URL format based on the user-provided documentation.
URL = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{PAIR_ADDRESS}/ohlcv"

def fetch_sol_price_history():
    """
    Fetches historical price data for SOL/USDC for a specific problematic period
    using a known high-liquidity pair address.
    """
    if not API_KEY:
        print("BŁĄD: Klucz MORALIS_API_KEY nie został znaleziony w pliku .env")
        return

    print(f"Odpytuję adres URL: {URL}")

    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }
    
    # Target the problematic period with a buffer
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2025, 7, 12)

    params = {
        "timeframe": "1d",
        "currency": "usd",
        "fromDate": start_date.strftime('%Y-%m-%d'),
        "toDate": end_date.strftime('%Y-%m-%d')
    }

    print(f"\nParametry zapytania: {params}")

    try:
        response = requests.get(URL, headers=headers, params=params, timeout=20)
        
        print(f"\nStatus odpowiedzi: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n--- OTRZYMANE DANE (RAW) ---")
            print(json.dumps(data, indent=2))
            
            api_result = data.get('result', []) if isinstance(data, dict) else []
            
            if api_result:
                print("\n--- PRZETWORZONE WYNIKI ---")
                for candle in api_result:
                    ts_str = candle['timestamp']
                    # Handle ISO format with 'Z'
                    date_obj = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    date_str_formatted = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"Data: {date_str_formatted}, Cena zamknięcia (USD): {candle['close']}")
            else:
                print("\nAPI zwróciło pusty zestaw danych.")

        else:
            print("\nBŁĄD: Nie udało się pobrać danych.")
            print(f"Treść odpowiedzi: {response.text}")

    except requests.RequestException as e:
        print(f"\nKrytyczny błąd zapytania: {e}")

if __name__ == "__main__":
    fetch_sol_price_history()