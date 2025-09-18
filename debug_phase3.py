import pandas as pd
import sys
import os
import logging

# Konfiguracja logowania, aby widzieć komunikaty z modułów
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dodaj ścieżkę projektu do ścieżek Pythona, aby importy działały
# Upewnij się, że ta ścieżka jest poprawna dla Twojej struktury folderów
try:
    project_root = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, project_root)
    print(f"Dodano do ścieżki: {project_root}")
except NameError:
    # W przypadku interaktywnego uruchomienia
    project_root = os.path.abspath('.')
    sys.path.insert(0, project_root)
    print(f"Dodano do ścieżki (interaktywnie): {project_root}")


# Importujemy potrzebne moduły z Twojego projektu
try:
    from reporting.visualizations.interactive import tls_4d_grid_charts
    print("Moduły projektu zaimportowano pomyślnie.")
except ImportError as e:
    print(f"Błąd importu: {e}")
    print("Upewnij się, że skrypt debug_phase3.py jest w głównym folderze projektu.")
    sys.exit(1)

def load_simulation_data():
    """
    Funkcja ładująca dane na podstawie logiki znalezionej w html_report_generator.py.
    """
    print("\n--- Ładowanie Danych Symulacji ---")
    
    tls_results_df = None
    strategy_instances_df = None
    baseline_data = None

    # --- 1. Ładowanie wyników symulacji TLS ---
    # Na podstawie specyfikacji, zakładamy domyślną ścieżkę.
    # Jeśli jest inna, zmień ją tutaj.
    tls_results_path = 'reporting/output/tls_detailed_results.csv'
    print(f"Próba załadowania wyników TLS z: {tls_results_path}")
    if os.path.exists(tls_results_path):
        tls_results_df = pd.read_csv(tls_results_path)
        print(f"Załadowano {len(tls_results_df)} wierszy z tls_simulation_results.csv.")
    else:
        print(f"[BŁĄD] Nie znaleziono pliku: {tls_results_path}")

    # --- 2. Ładowanie danych instancji strategii ---
    # Logika z _generate_tls_4d_grid_charts
    strategy_instances_path = 'strategy_instances.csv'
    print(f"Próba załadowania instancji strategii z: {strategy_instances_path}")
    if os.path.exists(strategy_instances_path):
        strategy_instances_df = pd.read_csv(strategy_instances_path)
        print(f"Załadowano {len(strategy_instances_df)} wierszy z strategy_instances.csv.")
    else:
        print(f"[BŁĄD] Nie znaleziono pliku: {strategy_instances_path}")
    
    # --- 3. Ładowanie i obliczanie danych bazowych (baseline) ---
    # Logika z _generate_tls_4d_grid_charts
    baseline_path = 'reporting/output/range_test_aggregated.csv'
    print(f"Próba załadowania danych bazowych z: {baseline_path}")
    if os.path.exists(baseline_path):
        try:
            agg_df = pd.read_csv(baseline_path)
            # Znajdź najlepszą kombinację TP/SL dla każdej strategii
            optimal_df = agg_df.loc[agg_df.groupby('strategy_instance_id')['total_pnl'].idxmax()]
            baseline_data = optimal_df.set_index('strategy_instance_id')['total_pnl'].to_dict()
            print(f"Obliczono dane bazowe dla {len(baseline_data)} strategii.")
        except Exception as e:
            print(f"[BŁĄD] Nie udało się przetworzyć pliku baseline: {e}")
    else:
        print(f"[BŁĄD] Nie znaleziono pliku: {baseline_path}")

    if tls_results_df is None or strategy_instances_df is None or baseline_data is None:
        print("\nKRYTYCZNY BŁĄD: Nie udało się załadować wszystkich wymaganych danych.")
        print("Sprawdź powyższe komunikaty o błędach i popraw ścieżki.")
        sys.exit(1)
        
    print("Wszystkie dane załadowane pomyślnie.")
    return tls_results_df, strategy_instances_df, baseline_data

def run_debug_phase1(tls_df, strategy_df):
    """Analiza integralności danych."""
    print("\n--- Faza 1: Analiza Danych Wejściowych ---")
    
    print("\n[INFO] tls_results_df (pierwsze 5 wierszy):")
    print(tls_df.head())
    
    print("\n[TYPY DANYCH] tls_results_df:")
    tls_df.info()
    
    print("\n[STATYSTYKI] simulated_pnl w tls_results_df:")
    print(tls_df['simulated_pnl'].describe())
    
    print("\n[INFO] strategy_instances_df (pierwsze 5 wierszy):")
    print(strategy_df.head())

    print("\n[STATYSTYKI] total_invested w strategy_instances_df:")
    if 'total_invested' in strategy_df.columns:
        print(strategy_df['total_invested'].describe())
    else:
        print("[BŁĄD] Brak kolumny 'total_invested' w strategy_instances_df!")

    tls_strategies = set(tls_df['strategy_instance_id'].unique())
    instance_strategies = set(strategy_df['strategy_instance_id'].unique())
    
    print(f"\nLiczba unikalnych strategii w tls_results_df: {len(tls_strategies)}")
    print(f"Liczba unikalnych strategii w strategy_instances_df: {len(instance_strategies)}")
    
    if not tls_strategies.issubset(instance_strategies):
        print("\n[OSTRZEŻENIE] Niektóre strategie z wyników TLS nie mają odpowiednika w instancjach strategii!")
        print(f"Brakujące strategie: {tls_strategies - instance_strategies}")
    else:
        print("\n[OK] Wszystkie strategie z wyników TLS mają swoje dane w instancjach strategii.")

    if not tls_strategies:
        print("\n[BŁĄD] Brak jakichkolwiek strategii w danych. Nie można kontynuować.")
        return None
        
    test_strategy = sorted(list(tls_strategies), reverse=True)[0] # Bierzemy najnowszą
    print(f"\nWybrano najnowszą strategię do testów w Fazie 2: '{test_strategy}'")
    return test_strategy


def run_debug_phase2(tls_df, strategy_df, baseline_data, test_strategy_id):
    """Testowanie logiki generowania siatki."""
    print("\n--- Faza 2: Testowanie Logiki Siatki ---")

    print("\n[TEST 1] Generowanie siatki dla 'Wszystkich Strategii'")
    grid_data_all = tls_4d_grid_charts.create_4d_tls_grid(
        tls_results_df=tls_df,
        strategy_filter='all',
        strategy_instances_df=strategy_df,
        baseline_data=baseline_data
    )

    if grid_data_all.get('error'):
        print(f"Błąd podczas generowania siatki dla wszystkich strategii: {grid_data_all['error']}")
    else:
        print("[OK] Siatka dla wszystkich strategii wygenerowana (bez błędów).")
        color_config = grid_data_all.get('global_color_config', {})
        print(f"  - Globalna skala kolorów: Min={color_config.get('global_min_pnl'):.4f}, Max={color_config.get('global_max_pnl'):.4f}")
        
        if grid_data_all['grid_data']:
            first_cell = grid_data_all['grid_data'][0][0]
            if first_cell.get('has_data'):
                print(f"  - Pierwsza komórka (Act: {first_cell['tls_activation']}, Trail: {first_cell['tls_trail']}) zawiera dane.")
                print(f"    - Najlepszy PnL: {first_cell.get('best_performance'):.2f}%")
                print(f"    - Wygenerowano HTML: {'Tak' if first_cell.get('heatmap_html') else 'Nie'}")
            else:
                 print("  - Pierwsza komórka siatki jest pusta.")
        else:
            print("  - [BŁĄD] Siatka nie zawiera żadnych danych (pusta lista 'grid_data').")

    print(f"\n[TEST 2] Generowanie siatki dla strategii: '{test_strategy_id}'")
    grid_data_single = tls_4d_grid_charts.create_4d_tls_grid(
        tls_results_df=tls_df,
        strategy_filter=test_strategy_id,
        strategy_instances_df=strategy_df,
        baseline_data=baseline_data
    )

    if grid_data_single.get('error'):
        print(f"Błąd podczas generowania siatki dla strategii '{test_strategy_id}': {grid_data_single['error']}")
    elif not grid_data_single.get('grid_data'):
        print(f"[BŁĄD] Siatka dla strategii '{test_strategy_id}' jest PUSTA. To prawdopodobnie źródło problemu!")
        print("  - Sprawdź, czy na pewno istnieją dane dla tej strategii w pliku tls_results_df.")
    else:
        print(f"[OK] Siatka dla strategii '{test_strategy_id}' wygenerowana (bez błędów).")
        color_config = grid_data_single.get('global_color_config', {})
        print(f"  - Lokalna skala kolorów: Min={color_config.get('global_min_pnl'):.4f}, Max={color_config.get('global_max_pnl'):.4f}")
        
        first_cell = grid_data_single['grid_data'][0][0]
        if first_cell.get('has_data'):
            print(f"  - Pierwsza komórka (Act: {first_cell['tls_activation']}, Trail: {first_cell['tls_trail']}) zawiera dane.")
            print(f"    - Najlepszy PnL: {first_cell.get('best_performance'):.2f}%")
            print(f"    - Wygenerowano HTML: {'Tak' if first_cell.get('heatmap_html') else 'Nie'}")
        else:
             print("  - Pierwsza komórka siatki jest pusta.")

if __name__ == '__main__':
    # Krok 1: Załaduj dane
    try:
        tls_results_df, strategy_instances_df, baseline_data = load_simulation_data()
        
        # Krok 2: Uruchom analizę danych wejściowych
        test_strategy = run_debug_phase1(tls_results_df, strategy_instances_df)

        # Krok 3: Jeśli dane są OK, uruchom test logiki siatki
        if test_strategy:
            run_debug_phase2(tls_results_df, strategy_instances_df, baseline_data, test_strategy)

    except SystemExit as e:
        print(f"\nSkrypt zakończony z powodu błędu: {e}")
    except Exception as e:
        print(f"\nNiespodziewany błąd podczas uruchamiania skryptu: {e}")
        import traceback
        traceback.print_exc()