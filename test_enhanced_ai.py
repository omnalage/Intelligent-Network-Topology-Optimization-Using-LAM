# test_enhanced_ai.py
"""
Test script for enhanced AI network recommender with advanced ML/DL ensemble.
Generates comprehensive performance metrics and plots.
"""

import os
import sys
import pickle
from ai_network_recommender_enhanced import collect_network_metrics, enhanced_ensemble_train_and_predict
from plot_performance_metrics import plot_all_performance_metrics, plot_metric_comparison
from comparison_ai_icn import compare_ai_vs_icn

# Try to import network setup
try:
    from main import setup_network, load_network
    MAIN_AVAILABLE = True
except Exception:
    MAIN_AVAILABLE = False
    print("[test_enhanced_ai] Warning: main.py not available, will use synthetic data if needed")


def main():
    print("=" * 80)
    print("ENHANCED AI NETWORK RECOMMENDER WITH ML/DL ENSEMBLE")
    print("=" * 80)
    
    routers = None
    publishers = None
    subscribers = None
    
    # Try to load network from saved file
    network_file = "Saved_Network/network_setup.pkl"
    if os.path.exists(network_file):
        try:
            print(f"\n[+] Loading network from {network_file}...")
            with open(network_file, 'rb') as f:
                network_data = pickle.load(f)
            
            # Handle both tuple and dict formats
            if isinstance(network_data, tuple):
                routers, publishers, subscribers = network_data
            elif isinstance(network_data, dict):
                routers = network_data.get('routers', None)
                publishers = network_data.get('publishers', None)
                subscribers = network_data.get('subscribers', None)
            
            if routers:
                print(f"[+] Loaded network with {len(routers)} routers")
            else:
                print("[!] No routers found in saved network")
        except Exception as e:
            print(f"[!] Failed to load network: {e}")
            routers = None
    
    # If no network loaded, try to create one
    if routers is None and MAIN_AVAILABLE:
        try:
            print("\n[+] Creating new network...")
            routers, publishers, subscribers = setup_network()
            print(f"[+] Created network with {len(routers)} routers")
        except Exception as e:
            print(f"[!] Failed to create network: {e}")
            routers = None
    
    # If still no routers, use synthetic data
    if routers is None:
        print("\n[!] No router objects available. Using synthetic data generation.")
        print("[!] Note: Hop reduction calculation will be simplified.")
        routers = []
    
    # Step 1: Collect network metrics
    print("\n" + "=" * 80)
    print("STEP 1: COLLECTING NETWORK METRICS")
    print("=" * 80)
    
    n_iterations = 50  # Adjust as needed
    metrics_csv = "Path_Iterations/network_metrics.csv"
    
    if routers:
        print(f"[+] Collecting metrics for {len(routers)} routers over {n_iterations} iterations...")
        metrics_csv = collect_network_metrics(
            routers=routers,
            n_iterations=n_iterations,
            perturb=True,
            out_csv=metrics_csv
        )
    else:
        print("[!] No routers available, skipping metric collection.")
        print("[!] If you have an existing metrics CSV, it will be used.")
        if not os.path.exists(metrics_csv):
            print(f"[!] Error: {metrics_csv} not found and no routers to generate data.")
            return
    
    # Step 2: Train enhanced ensemble and generate predictions
    print("\n" + "=" * 80)
    print("STEP 2: TRAINING ENHANCED ML/DL ENSEMBLE")
    print("=" * 80)
    
    try:
        result = enhanced_ensemble_train_and_predict(
            metrics_csv=metrics_csv,
            selection_out="Path_Iterations/network_selection_history.csv",
            min_iters_for_training=8,
            routers=routers if routers else None
        )
        
        print(f"\n[+] Model used: {result['model_used']}")
        if result['model_used']:
            print(f"[+] Ensemble components: {result.get('model_components', [])}")
        
        print(f"[+] Performance metrics saved to: Path_Iterations/performance_metrics.csv")
        print(f"[+] Selection history saved to: Path_Iterations/network_selection_history.csv")
        
        # Display summary statistics
        if 'performance_metrics_df' in result and not result['performance_metrics_df'].empty:
            perf_df = result['performance_metrics_df']
            print("\n[+] Performance Metrics Summary:")
            print(perf_df.describe())
            
    except Exception as e:
        print(f"[!] Error in enhanced ensemble training: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Generate comprehensive plots
    print("\n" + "=" * 80)
    print("STEP 3: GENERATING PERFORMANCE METRIC PLOTS")
    print("=" * 80)
    
    try:
        plot_paths = plot_all_performance_metrics(
            metrics_csv="Path_Iterations/performance_metrics.csv",
            save_plots=True,
            show_plots=False
        )
        
        print("\n[+] Generated plots:")
        for key, path in plot_paths.items():
            print(f"    - {key}: {path}")
            
    except Exception as e:
        print(f"[!] Error generating plots: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Compare AI vs ICN
    print("\n" + "=" * 80)
    print("STEP 4: COMPARING AI vs ICN")
    print("=" * 80)
    
    try:
        comparison_result = compare_ai_vs_icn(
            metrics_csv=metrics_csv,
            selection_csv="Path_Iterations/network_selection_history.csv",
            save_plots=True
        )
        
        print("\n[+] AI vs ICN comparison complete!")
        print("\n[+] Comparison Summary:")
        if 'summary_df' in comparison_result:
            print(comparison_result['summary_df'].to_string(index=False))
            
    except Exception as e:
        print(f"[!] Error in AI vs ICN comparison: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("ENHANCED AI RECOMMENDER TEST COMPLETE")
    print("=" * 80)
    print("\n[+] Check Path_Iterations/plots/ for all generated visualizations")
    print("[+] Check Path_Iterations/performance_metrics.csv for detailed metrics")


if __name__ == "__main__":
    main()

