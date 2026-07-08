"""Check why ICN cache occupancy is 0"""
import pandas as pd
from comparison_ai_icn import compute_icn_selection

df = pd.read_csv('Path_Iterations/network_metrics.csv')
icn = compute_icn_selection('Path_Iterations/network_metrics.csv')

print("Sample metrics from CSV:")
print(df[['iteration', 'Router', 'CacheOccupancy', 'CHR', 'Latency_ms']].head(15))
print("\n" + "="*80)
print("ICN selections and their cache occupancy:")
print("="*80)

icn_metrics = []
for it in sorted(df['iteration'].unique())[:10]:
    router = icn.get(it)
    if router:
        row = df[(df['iteration']==it) & (df['Router']==router)]
        if not row.empty:
            cache_occ = row['CacheOccupancy'].values[0]
            chr_val = row['CHR'].values[0]
            latency = row['Latency_ms'].values[0]
            print(f"Iter {it}: {router} -> CacheOccupancy={cache_occ}, CHR={chr_val:.3f}, Latency={latency:.2f}ms")
            icn_metrics.append(cache_occ)

print(f"\nAverage Cache Occupancy for ICN (first 10 iters): {sum(icn_metrics)/len(icn_metrics) if icn_metrics else 0}")

# Check all iterations
all_icn_metrics = []
for it in sorted(df['iteration'].unique()):
    router = icn.get(it)
    if router:
        row = df[(df['iteration']==it) & (df['Router']==router)]
        if not row.empty:
            all_icn_metrics.append(row['CacheOccupancy'].values[0])

print(f"Average Cache Occupancy for ICN (all {len(all_icn_metrics)} iterations): {sum(all_icn_metrics)/len(all_icn_metrics) if all_icn_metrics else 0}")
print(f"Min: {min(all_icn_metrics) if all_icn_metrics else 0}, Max: {max(all_icn_metrics) if all_icn_metrics else 0}")

# Check how many routers have 0 cache occupancy
print(f"\nRouters with 0 cache occupancy: {sum(1 for x in all_icn_metrics if x == 0)}/{len(all_icn_metrics)}")


