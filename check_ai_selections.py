"""Check AI selections cache occupancy"""
import pandas as pd

df_sel = pd.read_csv('Path_Iterations/network_selection_history.csv')
df_metrics = pd.read_csv('Path_Iterations/network_metrics.csv')

print("AI selections sample:")
print(df_sel.head(10))
print("\n" + "="*80)
print("AI-selected router metrics (first 10 iterations):")
print("="*80)

ai_cache_occ = []
for it in sorted(df_sel['iteration'].unique())[:10]:
    router = df_sel[df_sel['iteration']==it]['best_by_model'].values[0]
    row = df_metrics[(df_metrics['iteration']==it) & (df_metrics['Router']==router)]
    if not row.empty:
        cache_occ = row['CacheOccupancy'].values[0]
        chr_val = row['CHR'].values[0]
        latency = row['Latency_ms'].values[0]
        print(f"Iter {it}: {router} -> CacheOccupancy={cache_occ}, CHR={chr_val:.3f}, Latency={latency:.2f}ms")
        ai_cache_occ.append(cache_occ)

# Check all
all_ai_cache = []
for it in sorted(df_sel['iteration'].unique()):
    router = df_sel[df_sel['iteration']==it]['best_by_model'].values[0]
    row = df_metrics[(df_metrics['iteration']==it) & (df_metrics['Router']==router)]
    if not row.empty:
        all_ai_cache.append(row['CacheOccupancy'].values[0])

print(f"\nAverage Cache Occupancy for AI (all {len(all_ai_cache)} iterations): {sum(all_ai_cache)/len(all_ai_cache) if all_ai_cache else 0}")
print(f"Min: {min(all_ai_cache) if all_ai_cache else 0}, Max: {max(all_ai_cache) if all_ai_cache else 0}")
print(f"Routers with 0 cache occupancy: {sum(1 for x in all_ai_cache if x == 0)}/{len(all_ai_cache)}")


