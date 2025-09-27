import pandas as pd

# Sprawdźmy strukturę pliku
df = pd.read_csv('reporting/output/range_test_aggregated.csv')
print("Kolumny w pliku:")
print(df.columns.tolist())
print(f"\nLiczba wierszy: {len(df)}")
print(f"Liczba strategii: {df['strategy_instance_id'].nunique() if 'strategy_instance_id' in df.columns else 'brak kolumny strategy_instance_id'}")
print("\nPierwsze 3 wiersze:")
print(df.head(3))