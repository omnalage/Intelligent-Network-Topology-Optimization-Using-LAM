"""
Comparison of AI-recommended routers vs CMBA-based (deterministic) routers.
Compares all 6 metrics:
1. CHR (Cache Hit Ratio)
2. LATENCY
3. HOP REDUCTION
4. DETECTION COST
5. PREDICTION TIME
6. ACCURACY
Creates comprehensive comparison plots.
"""

import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional

CSV_DIR = "Path_Iterations"
PLOT_DIR = os.path.join(CSV_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)


def _normalize_per_iteration(df: pd.DataFrame, col: str, higher_is_better: bool) -> pd.Series:
    """Normalize a column per iteration group."""
    s = pd.to_numeric(df[col], errors='coerce').astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0]*len(s), index=s.index)
    if higher_is_better:
        return (s - mn) / (mx - mn)
    else:
        return (mx - s) / (mx - mn)


def compute_cmba_selection(metrics_csv: str) -> Dict[int, str]:
    """
    Compute CMBA-based (deterministic) router selection for each iteration.
    Uses the same logic as ai_network_recommender: equal-weight scoring.
    
    Returns:
        Dictionary mapping iteration -> router name (best_by_score)
    """
    df = pd.read_csv(metrics_csv)
    
    # Normalize per iteration and compute avg_score
    df_sorted = df.sort_values(['iteration','Router']).reset_index(drop=True)
    normalized = []
    for it, group in df_sorted.groupby('iteration', sort=True):
        g = group.copy().reset_index(drop=True)
        g['n_CMBA'] = _normalize_per_iteration(g, 'CMBA', higher_is_better=True)
        g['n_CHR'] = _normalize_per_iteration(g, 'CHR', higher_is_better=True)
        g['n_Latency'] = _normalize_per_iteration(g, 'Latency_ms', higher_is_better=False)
        g['n_CacheOcc'] = _normalize_per_iteration(g, 'CacheOccupancy', higher_is_better=False)
        # Equal weights -> average
        g['avg_score_eq'] = g[['n_CMBA','n_CHR','n_Latency','n_CacheOcc']].mean(axis=1)
        normalized.append(g)
    df_norm = pd.concat(normalized, ignore_index=True)
    
    # Determine best_by_score per iteration (CMBA-based selection)
    # Note: Lower cache occupancy is better (already normalized), so routers with 0 occupancy are preferred
    best_by_score = {}
    for it, group in df_norm.groupby('iteration', sort=True):
        # Choose max avg_score_eq, break ties by CHR desc then Latency asc then Router name
        # The normalization already favors lower cache occupancy, so empty routers (0 occupancy) score higher
        sel = group.sort_values(by=['avg_score_eq','CHR','Latency_ms','Router'], 
                               ascending=[False,False,True,True]).iloc[0]
        best_by_score[it] = sel['Router']
    
    return best_by_score


def calculate_hop_reduction_for_router(router_name: str, df_norm: pd.DataFrame, iteration: int) -> float:
    """Calculate hop reduction for a selected router using CMBA and CHR."""
    router_data = df_norm[(df_norm['Router'] == router_name) & (df_norm['iteration'] == iteration)]
    if not router_data.empty:
        cmba = router_data['CMBA'].iloc[0]
        chr_val = router_data['CHR'].iloc[0]
        cmba_normalized = min(1.0, max(0.0, cmba / 10.0))
        hop_reduction = (cmba_normalized * 0.6 + chr_val * 0.4)
        return hop_reduction
    return 0.0


def compare_ai_vs_cmba(metrics_csv: str = "Path_Iterations/network_metrics.csv",
                     selection_csv: str = "Path_Iterations/network_selection_history.csv",
                     performance_metrics_csv: Optional[str] = None,
                     save_plots: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Compare AI-recommended routers vs CMBA-based routers.
    
    Args:
        metrics_csv: Path to network metrics CSV
        selection_csv: Path to selection history CSV (contains best_by_model)
        save_plots: Whether to save comparison plots
    
    Returns:
        Dictionary with comparison DataFrames and statistics
    """
    # Read data
    if not os.path.exists(metrics_csv):
        raise FileNotFoundError(f"Metrics CSV not found: {metrics_csv}")
    if not os.path.exists(selection_csv):
        raise FileNotFoundError(f"Selection CSV not found: {selection_csv}")
    
    df_metrics = pd.read_csv(metrics_csv)
    df_selection = pd.read_csv(selection_csv)
    
    # Load AI performance metrics if available
    df_ai_perf = None
    if performance_metrics_csv and os.path.exists(performance_metrics_csv):
        df_ai_perf = pd.read_csv(performance_metrics_csv)
        print(f"[compare_ai_vs_cmba] Loaded AI performance metrics from {performance_metrics_csv}")
    else:
        # Try default location
        default_perf = "Path_Iterations/performance_metrics.csv"
        if os.path.exists(default_perf):
            df_ai_perf = pd.read_csv(default_perf)
            print(f"[compare_ai_vs_cmba] Loaded AI performance metrics from {default_perf}")
    
    # Compute CMBA-based selection (best_by_score) with normalized data for hop reduction calculation
    print("[compare_ai_vs_cmba] Computing CMBA-based selections...")
    cmba_selections = compute_cmba_selection(metrics_csv)
    
    # Build normalized dataframe for hop reduction calculation
    df_sorted = df_metrics.sort_values(['iteration','Router']).reset_index(drop=True)
    normalized = []
    for it, group in df_sorted.groupby('iteration', sort=True):
        g = group.copy().reset_index(drop=True)
        g['n_CMBA'] = _normalize_per_iteration(g, 'CMBA', higher_is_better=True)
        g['n_CHR'] = _normalize_per_iteration(g, 'CHR', higher_is_better=True)
        g['n_Latency'] = _normalize_per_iteration(g, 'Latency_ms', higher_is_better=False)
        g['n_CacheOcc'] = _normalize_per_iteration(g, 'CacheOccupancy', higher_is_better=False)
        g['avg_score_eq'] = g[['n_CMBA','n_CHR','n_Latency','n_CacheOcc']].mean(axis=1)
        normalized.append(g)
    df_norm = pd.concat(normalized, ignore_index=True)
    
    # Get AI selections (best_by_model)
    if 'best_by_model' not in df_selection.columns:
        raise ValueError("Selection CSV must contain 'best_by_model' column")
    
    ai_selections = dict(zip(df_selection['iteration'], df_selection['best_by_model']))
    
    # Collect ALL 6 metrics for each selected router per iteration
    ai_metrics = []
    cmba_metrics = []
    
    for iteration in sorted(df_metrics['iteration'].unique()):
        iter_data = df_metrics[df_metrics['iteration'] == iteration]
        
        # Get AI-selected router metrics
        ai_router = ai_selections.get(iteration)
        cmba_router = cmba_selections.get(iteration)
        
        # AI metrics (from performance_metrics.csv if available, otherwise calculate)
        ai_chr = ai_latency = ai_hop_reduction = ai_detection_cost = ai_prediction_time = ai_accuracy = 0.0
        
        if df_ai_perf is not None:
            ai_perf_row = df_ai_perf[df_ai_perf['iteration'] == iteration]
            if not ai_perf_row.empty:
                ai_chr = float(ai_perf_row['CHR'].iloc[0])
                ai_latency = float(ai_perf_row['Latency'].iloc[0])
                ai_hop_reduction = float(ai_perf_row['HopReduction'].iloc[0])
                ai_detection_cost = float(ai_perf_row['DetectionCost'].iloc[0])
                ai_prediction_time = float(ai_perf_row['PredictionTime'].iloc[0])
                ai_accuracy = float(ai_perf_row['Accuracy'].iloc[0])
        else:
            # Fallback: calculate from metrics if performance CSV not available
            if ai_router:
                ai_row = iter_data[iter_data['Router'] == ai_router]
                if not ai_row.empty:
                    ai_chr = float(ai_row['CHR'].iloc[0])
                    ai_latency = float(ai_row['Latency_ms'].iloc[0])
                    ai_hop_reduction = calculate_hop_reduction_for_router(ai_router, df_norm, iteration)
                    ai_detection_cost = 0.0  # AI doesn't have detection cost
                    ai_prediction_time = 0.0  # Not available without performance CSV
                    ai_accuracy = 1.0 if ai_router == cmba_router else 0.0
        
        if ai_router:
            ai_metrics.append({
                'iteration': iteration,
                'Router': ai_router,
                'CHR': ai_chr,
                'Latency': ai_latency,
                'HopReduction': ai_hop_reduction,
                'DetectionCost': ai_detection_cost,
                'PredictionTime': ai_prediction_time,
                'Accuracy': ai_accuracy
            })
        
        # CMBA-based metrics
        if cmba_router:
            cmba_row = iter_data[iter_data['Router'] == cmba_router]
            if not cmba_row.empty:
                # Calculate detection cost (time to compute CMBA-based selection for this iteration)
                # CMBA-based is just sorting/normalization - very fast per iteration
                detection_start = time.perf_counter()
                iter_group = df_norm[df_norm['iteration'] == iteration]
                _ = iter_group.sort_values(by=['avg_score_eq','CHR','Latency_ms','Router'], 
                                         ascending=[False,False,True,True]).iloc[0]
                detection_cost = (time.perf_counter() - detection_start) * 1000  # Convert to ms
                
                cmba_metrics.append({
                    'iteration': iteration,
                    'Router': cmba_router,
                    'CHR': float(cmba_row['CHR'].iloc[0]),
                    'Latency': float(cmba_row['Latency_ms'].iloc[0]),
                    'HopReduction': calculate_hop_reduction_for_router(cmba_router, df_norm, iteration),
                    'DetectionCost': detection_cost,
                    'PredictionTime': 0.0,  # CMBA-based is deterministic, no ML prediction
                    'Accuracy': 1.0  # CMBA-based always matches itself (optimal)
                })
    
    df_ai = pd.DataFrame(ai_metrics)
    df_cmba = pd.DataFrame(cmba_metrics)
    
    # Calculate averages for ALL 6 metrics
    metrics_list = ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']
    metric_labels = [
        'CHR (Cache Hit Ratio)',
        'Latency (ms)',
        'Hop Reduction',
        'Detection Cost (ms)',
        'Prediction Time (ms)',
        'Accuracy'
    ]
    higher_is_better = [True, False, True, False, False, True]  # Which direction is better for each metric
    
    ai_avgs = []
    cmba_avgs = []
    differences = []
    improvements = []
    
    for metric, label, higher_better in zip(metrics_list, metric_labels, higher_is_better):
        ai_avg = df_ai[metric].mean() if not df_ai.empty and metric in df_ai.columns else 0.0
        cmba_avg = df_cmba[metric].mean() if not df_cmba.empty and metric in df_cmba.columns else 0.0
        diff = ai_avg - cmba_avg
        
        # Calculate improvement percentage
        if higher_better:
            # Higher is better (CHR, HopReduction, Accuracy)
            improvement = ((ai_avg - cmba_avg) / cmba_avg * 100) if cmba_avg != 0 else 0.0
        else:
            # Lower is better (Latency, DetectionCost, PredictionTime)
            improvement = ((cmba_avg - ai_avg) / cmba_avg * 100) if cmba_avg != 0 else 0.0
        
        ai_avgs.append(ai_avg)
        cmba_avgs.append(cmba_avg)
        differences.append(diff)
        improvements.append(improvement)
    
    comparison_stats = {
        'Metric': metric_labels,
        'AI Average': ai_avgs,
        'CMBA Average': cmba_avgs,
        'Difference (AI - CMBA)': differences,
        'Improvement %': improvements
    }
    
    df_comparison = pd.DataFrame(comparison_stats)
    
    # Print summary
    print("\n" + "=" * 80)
    print("AI vs CMBA COMPARISON SUMMARY")
    print("=" * 80)
    print(df_comparison.to_string(index=False))
    print("=" * 80)
    
    # Create comparison plots
    if save_plots:
        create_comparison_plots(df_ai, df_cmba, df_comparison)
    
    return {
        'ai_metrics': df_ai,
        'cmba_metrics': df_cmba,
        'comparison_stats': df_comparison,
        'ai_selections': ai_selections,
        'cmba_selections': cmba_selections
    }


def create_comparison_plots(df_ai: pd.DataFrame, df_cmba: pd.DataFrame, df_comparison: pd.DataFrame):
    """Create comprehensive comparison plots for AI vs CMBA-based metrics (all 6 metrics)."""
    
    # 1. Bar chart comparing average metrics (all 6 metrics in 2x3 grid)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    
    metrics_list = ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']
    metric_labels = [
        'Cache Hit Ratio (CHR)',
        'Latency (ms)',
        'Hop Reduction',
        'Detection Cost (ms)',
        'Prediction Time (ms)',
        'Accuracy'
    ]
    colors = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']
    higher_is_better = [True, False, True, False, False, True]
    
    for idx, (metric, label, color, higher_better) in enumerate(zip(metrics_list, metric_labels, colors, higher_is_better)):
        ax = axes[idx]
        
        ai_avg = df_ai[metric].mean() if not df_ai.empty and metric in df_ai.columns else 0.0
        cmba_avg = df_cmba[metric].mean() if not df_cmba.empty and metric in df_cmba.columns else 0.0
        
        bars = ax.bar(['AI-Based', 'CMBA-based'], [ai_avg, cmba_avg], 
                     color=[color, color], alpha=0.7, width=0.6)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}' if metric in ['CHR', 'HopReduction', 'Accuracy'] else f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_ylabel(label, fontsize=10, fontweight='bold')
        ax.set_title(f'Average {label}', fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add improvement annotation
        if higher_better:
            improvement = ((ai_avg - cmba_avg) / cmba_avg * 100) if cmba_avg != 0 else 0.0
            improvement_text = f'AI: {improvement:+.1f}%'
        else:
            improvement = ((cmba_avg - ai_avg) / cmba_avg * 100) if cmba_avg != 0 else 0.0
            improvement_text = f'AI: {improvement:+.1f}% lower' if improvement >= 0 else f'AI: {abs(improvement):+.1f}% higher'
        
        ax.text(0.5, max(ai_avg, cmba_avg) * 1.15, 
               improvement_text,
               ha='center', fontsize=8, color='green' if improvement > 0 else 'red',
               fontweight='bold', transform=ax.transData)
    
    plt.suptitle('AI-Based vs CMBA-based Router Selection: Average Metrics Comparison (All 6 Metrics)', 
                fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    plot_path = os.path.join(PLOT_DIR, "ai_vs_cmba_average_comparison.png")
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"[create_comparison_plots] Saved average comparison plot: {plot_path}")
    plt.close()
    
    # 2. Line plot showing all 6 metrics over iterations (2x3 grid)
    if not df_ai.empty and not df_cmba.empty:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        metrics_list = ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']
        metric_labels = [
            'Cache Hit Ratio (CHR)',
            'Latency (ms)',
            'Hop Reduction',
            'Detection Cost (ms)',
            'Prediction Time (ms)',
            'Accuracy'
        ]
        colors_list = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']
        markers = ['o', 's', '^', 'v', 'D', 'x']
        
        for idx, (metric, label, color, marker) in enumerate(zip(metrics_list, metric_labels, colors_list, markers)):
            ax = axes[idx]
            
            # Plot AI and CMBA-based metrics over iterations
            ax.plot(df_ai['iteration'], df_ai[metric], marker=marker, linestyle='-', 
                   label='AI-Based', linewidth=2, markersize=5, color=color, alpha=0.8)
            ax.plot(df_cmba['iteration'], df_cmba[metric], marker=marker, linestyle='--', 
                   label='CMBA-based', linewidth=2, markersize=5, color=color, alpha=0.6)
            
            ax.set_xlabel('Iteration', fontsize=10)
            ax.set_ylabel(label, fontsize=10, fontweight='bold')
            ax.set_title(f'{label} Over Iterations', fontsize=11, fontweight='bold')
            ax.legend(loc='best', fontsize=9)
            ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.suptitle('AI-Based vs CMBA-based Router Selection: All Metrics Over Iterations', 
                    fontsize=14, fontweight='bold', y=1.00)
        plt.tight_layout()
        
        plot_path = os.path.join(PLOT_DIR, "ai_vs_cmba_iterations_comparison.png")
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"[create_comparison_plots] Saved iterations comparison plot: {plot_path}")
        plt.close()
    
    # 3. Summary statistics table plot
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('tight')
    ax.axis('off')
    
    # Prepare table data
    table_data = []
    for _, row in df_comparison.iterrows():
        table_data.append([
            row['Metric'],
            f"{row['AI Average']:.4f}",
            f"{row['CMBA Average']:.4f}",
            f"{row['Difference (AI - CMBA)']:+.4f}",
            f"{row['Improvement %']:+.2f}%"
        ])
    
    table = ax.table(cellText=table_data,
                     colLabels=['Metric', 'AI Average', 'CMBA Average', 'Difference', 'Improvement %'],
                     cellLoc='center',
                     loc='center',
                     colWidths=[0.3, 0.15, 0.15, 0.15, 0.15])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Style header
    for i in range(5):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color code improvements
    for i in range(1, len(table_data) + 1):
        improvement = float(table_data[i-1][4].replace('%', ''))
        if improvement > 0:
            table[(i, 4)].set_facecolor('#d4edda')
        elif improvement < 0:
            table[(i, 4)].set_facecolor('#f8d7da')
    
    plt.title('AI vs CMBA Comparison: Summary Statistics', fontsize=12, fontweight='bold', pad=20)
    
    plot_path = os.path.join(PLOT_DIR, "ai_vs_cmba_summary_table.png")
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"[create_comparison_plots] Saved summary table: {plot_path}")
    plt.close()


if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("AI vs CMBA ROUTER SELECTION COMPARISON")
    print("=" * 80)
    
    # Try to find available files
    metrics_csv = None
    selection_csv = None
    
    # Check for regular network files first
    if os.path.exists("Path_Iterations/network_metrics.csv"):
        metrics_csv = "Path_Iterations/network_metrics.csv"
        selection_csv = "Path_Iterations/network_selection_history.csv"
    elif os.path.exists("Path_Iterations/network_demo_metrics.csv"):
        metrics_csv = "Path_Iterations/network_demo_metrics.csv"
        selection_csv = "Path_Iterations/network_demo_selection.csv"
    
    # Allow command line override
    if len(sys.argv) > 1:
        metrics_csv = sys.argv[1]
    if len(sys.argv) > 2:
        selection_csv = sys.argv[2]
    
    # Check if files exist
    if not metrics_csv or not os.path.exists(metrics_csv):
        print(f"Error: Metrics CSV not found.")
        print(f"Please run test.py first to generate metrics, or provide path as argument.")
        print(f"Usage: python comparison_ai_icn.py [metrics_csv] [selection_csv]")
        exit(1)
    
    if not selection_csv or not os.path.exists(selection_csv):
        print(f"Error: Selection CSV not found.")
        print(f"Please run test.py first to generate selections, or provide path as argument.")
        print(f"Usage: python comparison_ai_icn.py [metrics_csv] [selection_csv]")
        exit(1)
    
    print(f"Using metrics CSV: {metrics_csv}")
    print(f"Using selection CSV: {selection_csv}")
    
    # Run comparison
    results = compare_ai_vs_cmba(metrics_csv, selection_csv, save_plots=True)
    
    print("\n[+] Comparison complete! Check Path_Iterations/plots/ for visualization files:")
    print("    - ai_vs_cmba_average_comparison.png")
    print("    - ai_vs_cmba_iterations_comparison.png")
    print("    - ai_vs_cmba_summary_table.png")

