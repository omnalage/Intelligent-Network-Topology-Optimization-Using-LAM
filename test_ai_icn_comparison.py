"""
Test script to regenerate network metrics and compare AI vs ICN
"""
from main import setup_network, load_network
from ai_network_recommender import collect_network_metrics, equal_weight_select_and_train
import os
import pickle

print("=" * 80)
print("GENERATING NETWORK METRICS AND COMPARING AI vs ICN")
print("=" * 80)

# Load network
network_file = "Saved_Network/network_setup.pkl"
if os.path.exists(network_file):
    try:
        with open(network_file, 'rb') as f:
            network_data = pickle.load(f)
            if isinstance(network_data, tuple):
                routers, publishers, subscribers = network_data
            else:
                routers = network_data
        print(f"[+] Loaded network with {len(routers)} routers")
    except Exception as e:
        print(f"[!] Could not load network: {e}")
        print("[!] Please run main.py first to create a network")
        exit(1)
else:
    print("[!] Network file not found. Please run main.py first to create a network")
    exit(1)

# Generate metrics
print("\n[+] Collecting network metrics...")
csv_path = collect_network_metrics(routers, n_iterations=50, perturb=True, 
                                   out_csv="Path_Iterations/network_metrics.csv")

# Train and get selections
print("\n[+] Training AI model and generating selections...")
res = equal_weight_select_and_train(csv_path, 
                                    selection_out="Path_Iterations/network_selection_history.csv", 
                                    min_iters_for_training=8)

print(f"\n[+] Model used: {res['model_used']}")
print(f"[+] Selection history saved")

# Run comparison
print("\n[+] Running AI vs ICN comparison...")
from comparison_ai_icn import compare_ai_vs_icn
results = compare_ai_vs_icn("Path_Iterations/network_metrics.csv", 
                            "Path_Iterations/network_selection_history.csv", 
                            save_plots=True)

print("\n[+] Done! Check Path_Iterations/plots/ for comparison visualizations")


