import os
import random
import time
import csv
import pandas as pd

# --- Import all necessary components from your main.py ---
try:
    from main import (
        Router, Publisher, Subscriber, InterestPacket, 
        setup_network, compute_cmv, _build_graph_from_routers, 
        _all_pairs_shortest_paths_lengths, _closeness_centrality_from_sp
    )
except ImportError:
    print("Error: Could not import from main.py.")
    print("Please make sure 'manual_mode.py' is in the same directory as 'main.py'")
    exit()

# --- Configuration ---
PATH_TO_TRACE = ['Router1', 'Router4'] # The specific path you want to analyze
CACHE_LIMIT = Router.CACHE_LIMIT      # Get cache limit from your main.py Router class

# --- Global Dictionaries for new per-router metrics ---
ROUTER_CACHE_HITS = {}
ROUTER_REQUESTS = {}

def get_router_by_name(routers, name):
    """Helper function to find a router object by its name."""
    for router in routers:
        if router.name == name:
            return router
    return None

def reset_router_metrics(routers):
    """Resets all metrics for a new simulation run."""
    global ROUTER_CACHE_HITS, ROUTER_REQUESTS
    ROUTER_CACHE_HITS = {r.name: 0 for r in routers}
    ROUTER_REQUESTS = {r.name: 0 for r in routers}
    for r in routers:
        r.reset() # This calls the reset() method you defined in main.py

def calculate_router_performance(router, all_routers, cmv_scores, closeness_scores):
    """Calculates the net performance scores for a single router at a single point in time."""
    router_name = router.name
    
    # 1. CMBA Score
    cmv_score = cmv_scores.get(router_name, 0.0)
    
    # 2. Cache Occupy Score (1.0 = empty, 0.0 = full)
    cache_occupy_raw = len(router.cs) / CACHE_LIMIT
    cache_occupy_score = 1.0 - cache_occupy_raw
    
    # 3. Latency Score (Using Closeness Centrality as a proxy)
    # High closeness (e.g., 0.7) means low latency, so this score is good as is.
    latency_score = closeness_scores.get(router_name, 0.0)
    
    # 4. Cache Hit Ratio (CHR) Score for this router
    hits = ROUTER_CACHE_HITS.get(router_name, 0)
    requests = ROUTER_REQUESTS.get(router_name, 0)
    chr_score = (hits / requests) if requests > 0 else 0.0
        
    # 5. Average (Net Performance)
    # We weigh CHR and Latency higher as they are direct performance indicators
    net_performance = (cmv_score + cache_occupy_score + (latency_score * 1.5) + (chr_score * 1.5)) / 4.0
    
    return {
        "cmv_score": cmv_score,
        "cache_occupy_score": cache_occupy_score,
        "latency_score": latency_score,
        "chr_score": chr_score,
        "net_performance": net_performance
    }

def run_traced_simulation(routers, publisher, subscribers, iterations, path_to_trace, output_csv):
    """
    Runs a simulation while tracing and recording metrics for specific routers.
    """
    global ROUTER_CACHE_HITS, ROUTER_REQUESTS
    reset_router_metrics(routers)
    
    # Find the publisher object from the router's FIB
    # (Assuming Router1's FIB is set up)
    if not publisher:
        try:
            publisher = get_router_by_name(routers, "Router1").fib["cat_image1.jpg"]
            if isinstance(publisher, Router): # Find the *actual* publisher
                 publisher = get_router_by_name(routers, "Router10").fib["cat_image1.jpg"]
        except Exception as e:
            print(f"Could not auto-detect publisher: {e}")
            return
            
    all_content = list(publisher.images.keys())
    metrics_data = []
    
    # Pre-calculate full-network centralities once
    adj = _build_graph_from_routers(routers)
    all_sp = _all_pairs_shortest_paths_lengths(adj)
    cmv_scores = compute_cmv(routers)
    closeness_scores = _closeness_centrality_from_sp(all_sp)

    print(f"Running traced simulation for {iterations} iterations... Saving to {output_csv}")
    
    for i in range(iterations):
        subscriber = random.choice(subscribers)
        content_name = random.choice(all_content)
        
        # --- This is the core logic from main.py's simulation ---
        interest_packet = InterestPacket(content_name)
        # Find the subscriber's connected router
        subscriber.connected_router.receive_interest(interest_packet, subscriber, routers)
        # --- End of core logic ---
        
        # After each request, record metrics for the traced path
        for router_name in path_to_trace:
            router_obj = get_router_by_name(routers, router_name)
            if not router_obj:
                continue
                
            # Update request/hit counters
            # A request "touches" a router if it's in the interest path
            if router_name in interest_packet.path:
                ROUTER_REQUESTS[router_name] = ROUTER_REQUESTS.get(router_name, 0) + 1
                # Check if this router was the one that served the content
                if interest_packet.name in router_obj.cs:
                     ROUTER_CACHE_HITS[router_name] = ROUTER_CACHE_HITS.get(router_name, 0) + 1

            # Calculate performance for this iteration
            perf = calculate_router_performance(router_obj, routers, cmv_scores, closeness_scores)
            
            metrics_data.append([
                i + 1,
                router_name,
                perf["cmv_score"],
                perf["cache_occupy_score"],
                perf["latency_score"],
                perf["chr_score"],
                perf["net_performance"]
            ])

    # Save the collected data to CSV
    header = ["iteration", "router_name", "cmv_score", "cache_occupy_score", "latency_score", "chr_score", "net_performance"]
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(metrics_data)
        
    print(f"Traced data saved to {output_csv}")
    return pd.DataFrame(metrics_data, columns=header)


def run_manual_mode(routers, subscribers, iterations, path_to_trace):
    """
    Runs the simulation and provides a manual recommendation based on average scores.
    """
    print("\n--- Running Manual Process Mode ---")
    
    # Publisher object is not strictly needed for this sim, as receive_interest finds it
    df = run_traced_simulation(routers, None, subscribers, iterations, path_to_trace, "manual_metrics.csv")
    
    # Calculate the average net_performance for each router
    avg_scores = df.groupby('router_name')['net_performance'].mean()
    print("\nAverage Net Performance (Manual Mode):")
    print(avg_scores)
    
    # Select the router with the best average score
    best_router_manual = avg_scores.idxmax()
    print(f"\nManual Recommendation: Router '{best_router_manual}' has the highest average performance.")
    return "manual_metrics.csv"

# --- Main execution block ---

def main():
    # 1. Setup the network from main.py
    print("Setting up network...")
    # This function is from your main.py
    routers, publishers, subscribers = setup_network()
    
    # 2. Verify the path exists
    for r_name in PATH_TO_TRACE:
        if not get_router_by_name(routers, r_name):
            print(f"Error: The specified router '{r_name}' does not exist in the topology.")
            print("Please check the 'setup_network' function in main.py.")
            return
        
    iterations_input = input("Enter number of iterations for Manual Mode (e.g., 200): ")
    try:
        iterations = int(iterations_input)
    except ValueError:
        print("Invalid number. Defaulting to 200.")
        iterations = 200

    # 3. Run Manual Mode
    manual_csv = run_manual_mode(routers, subscribers, iterations, PATH_TO_TRACE)
    print(f"\nManual process complete. Metrics saved to {manual_csv}")

if __name__ == "__main__":
    main()