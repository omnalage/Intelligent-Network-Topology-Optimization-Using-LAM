"""
Script to explain router selection for caching.
Shows why a specific router was chosen as the best.
"""

from ai_recommender import explain_router_recommendation
import sys

if __name__ == "__main__":
    # Default CSV path
    csv_path = r"Path_Iterations\path_Router1_to_Router19.csv"
    iteration = 1
    
    # Allow command line arguments
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        iteration = int(sys.argv[2])
    
    print("=" * 80)
    print("ROUTER SELECTION EXPLANATION")
    print("=" * 80)
    
    try:
        explanation_df, best_router = explain_router_recommendation(csv_path, iteration)
        
        print(f"\n[Analysis for Iteration {iteration}]")
        print(f"\n[BEST ROUTER: {best_router['Router']}]")
        print(f"   Average Score: {best_router['avg_score']:.4f}")
        print(f"\n[Raw Metrics]")
        print(f"   - CMBA: {best_router['CMBA']:.4f}")
        print(f"   - CHR: {best_router['CHR']:.2f}%")
        print(f"   - Cache Occupancy: {best_router['CacheOccupancy']:.2f}")
        print(f"   - Latency: {best_router['Latency(s)']:.4f}s")
        print(f"\n[Normalized Metrics (0-1 scale)]")
        print(f"   - Normalized CMBA: {best_router['norm_CMBA']:.4f}")
        print(f"   - Normalized CHR: {best_router['norm_CHR']:.4f}")
        print(f"   - Normalized Cache: {best_router['norm_Cache']:.4f}")
        print(f"   - Normalized Latency: {best_router['norm_Latency']:.4f}")
        
        print(f"\n[All Routers Comparison (sorted by performance)]")
        print(explanation_df.to_string(index=False))
        
        print("\n" + "=" * 80)
        print("HOW THE SELECTION WORKS:")
        print("=" * 80)
        print("1. For each iteration, metrics are collected for all routers")
        print("2. Metrics are normalized to 0-1 scale (per iteration):")
        print("   - CMBA & CHR: Higher is better → (value - min) / (max - min)")
        print("   - Cache Occupancy & Latency: Lower is better → (max - value) / (max - min)")
        print("3. Average Score = mean(norm_CMBA, norm_CHR, norm_Cache, norm_Latency)")
        print("4. Router with HIGHEST average score is selected as best for caching")
        print("5. If ML ensemble is available, it predicts probabilities and selects highest")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

