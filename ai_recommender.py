# ai_recommender_trainer.py
"""
AI recommender trainer & predictor.

Usage:
    from ai_recommender_trainer import generate_ai_recommendations
    generate_ai_recommendations(csv_path="Path_Iterations/path_Router1_to_Router19.csv",
                                path_name="path_Router1_to_Router19",
                                min_iterations_for_training=8,
                                save_selection_history=True)

What it does:
 - Reads CSV with columns (iteration, Router, CacheOccupancy/cache occupy, CMBA, Latency(s) or Latency_ms, CHR)
 - Normalizes metrics per iteration and computes avg_score (same scheme as deterministic)
 - Derives labels per-row: 1 if router had highest avg_score in that iteration
 - Trains ensemble (RF, ET, GB), prunes weak learners via cross-val, produces VotingClassifier
 - Predicts "best router" for each iteration using model probabilities (soft voting)
 - Saves selection history CSV Path_Iterations/{path_name}_selection_history.csv with ai_recommend_router
"""
import os
if os.path.exists("Path_Iterations/network_metrics.csv"):
    os.remove("Path_Iterations/network_metrics.csv")
import math
import pandas as pd
import numpy as np

# sklearn is required for training. If not installed, function will fallback to deterministic rule.
try:
    from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier, VotingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

def _detect_column(df, candidates):
    """Return first candidate that exists in df columns (case-insensitive) or None."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None

def _normalize_series(s: pd.Series, higher_is_better: bool) -> pd.Series:
    s = pd.to_numeric(s, errors='coerce').astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0]*len(s), index=s.index)
    if higher_is_better:
        return (s - mn) / (mx - mn)
    else:
        return (mx - s) / (mx - mn)

def compute_avg_score_per_iteration(df, col_map):
    """
    df: DataFrame containing router rows (for many iterations)
    col_map: dict with keys 'cache', 'cmba', 'latency', 'chr' mapping to df column names
    Returns df with added norm_* columns and avg_score.
    """
    df2 = df.copy()
    # for each iteration, normalize the metrics across routers in that iteration
    norm_cmba = []
    norm_chr = []
    norm_cache = []
    norm_lat = []
    for it, group in df2.groupby('iteration', sort=True):
        norm_cmba.append(_normalize_series(group[col_map['cmba']], higher_is_better=True))
        norm_chr.append(_normalize_series(group[col_map['chr']], higher_is_better=True))
        norm_cache.append(_normalize_series(group[col_map['cache']], higher_is_better=False))
        norm_lat.append(_normalize_series(group[col_map['latency']], higher_is_better=False))
    # concat respecting group order
    df2['norm_CMBA'] = pd.concat(norm_cmba).sort_index()
    df2['norm_CHR']  = pd.concat(norm_chr).sort_index()
    df2['norm_Cache'] = pd.concat(norm_cache).sort_index()
    df2['norm_Latency'] = pd.concat(norm_lat).sort_index()
    df2['avg_score'] = df2[['norm_CMBA','norm_CHR','norm_Cache','norm_Latency']].mean(axis=1)
    return df2

def label_best_by_avg(df):
    """
    For each iteration, find router(s) with highest avg_score.
    Label rows with 1 if they are a chosen-best (break ties by CHR then lower latency).
    """
    labels = []
    for it, group in df.groupby('iteration', sort=True):
        # choose by avg_score, tie-break CHR desc, Latency asc
        best = group.sort_values(by=['avg_score', 'CHR', 'Latency(s)'],
                                 ascending=[False, False, True]).iloc[0]
        mask = (df['iteration'] == it) & (df['Router'] == best['Router'])
        labels.append(mask)
    # combine masks
    if labels:
        label_series = pd.concat(labels, axis=0)
        # label_series is boolean Series aligned to df index because masks used df indexing.
        # Convert to integer (1/0)
        y = label_series.astype(int)
    else:
        y = pd.Series([0]*len(df), index=df.index)
    return y

def _train_pruned_ensemble(X_np, y_np, min_models=2, cv=3):
    """
    Train RF, ET, GB; compute cross_val_score; keep models with score>=threshold,
    threshold = max(0.5, mean(all_scores)). Ensure at least min_models kept by top-N.
    Returns fitted VotingClassifier or None.
    """
    models = [
        ('rf', RandomForestClassifier(n_estimators=200, random_state=42)),
        ('et', ExtraTreesClassifier(n_estimators=200, random_state=42)),
        ('gb', GradientBoostingClassifier(n_estimators=200, random_state=42))
    ]
    scores = {}
    fitted_models = []
    # compute cv scores (adapt cv to data size)
    n = len(y_np)
    cv_use = min(cv, max(2, n)) if n >= 2 else 2
    for name, m in models:
        try:
            sc = cross_val_score(m, X_np, y_np, cv=cv_use, scoring='accuracy')
            scores[name] = float(np.mean(sc))
        except Exception:
            scores[name] = 0.0
    mean_score = float(np.mean(list(scores.values()))) if scores else 0.0
    threshold = max(0.5, mean_score)
    # keep models >= threshold
    keep = [m for (n,m) in models if scores.get(n,0.0) >= threshold]
    if len(keep) < min_models:
        # take top min_models
        sorted_models = sorted(models, key=lambda nm: scores.get(nm[0],0.0), reverse=True)
        keep = [m for (_,m) in sorted_models[:min_models]]
    # fit kept models
    estimators = []
    for m in keep:
        m.fit(X_np, y_np)
        estimators.append((type(m).__name__, m))
    if not estimators:
        return None, scores
    vc = VotingClassifier(estimators=estimators, voting='soft')
    vc.fit(X_np, y_np)
    return vc, scores

def generate_ai_recommendations(csv_path: str = r"Path_Iterations\path_Router1_to_Router19.csv",
                                path_name: str = r"Path_Iterations\path_Router1_to_Router19.csv",
                                min_iterations_for_training: int = 3,
                                save_selection_history: bool = True,
                                selection_out_dir: str = "Path_Iterations"):
    """
    Main function.
    - csv_path: Path to metrics CSV (one row per router per iteration).
    - path_name: label for path (used in output filename).
    - min_iterations_for_training: minimum distinct iterations to try training; else fall back.
    - Returns: dict with keys: 'selection_csv', 'used_ensemble', 'ensemble_scores', 'recommendations' (dict iter->router)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"{csv_path} not found")

    df = pd.read_csv(csv_path)
    # Normalize expected column names
    cache_col = _detect_column(df, ["CacheOccupancy", "Cache Occupy", "Cache occupy", "CacheOccupy", "Cache occupy"])
    cmba_col = _detect_column(df, ["CMBA", "cmba", "Cmba"])
    latency_col = _detect_column(df, ["Latency_ms", "Latency(s)", "Latency", "latency_ms"])
    chr_col = _detect_column(df, ["CHR", "Chr", "CHR%", "Cache Hit Ratio"])

    if any(c is None for c in [cache_col, cmba_col, latency_col, chr_col]):
        # try more flexible guesses and raise if missing
        # we will try common alternates
        raise ValueError(f"Could not detect required columns in CSV. Found: {list(df.columns)}")

    # Standardize column names used inside (so rest of code can rely on them)
    df = df.rename(columns={cache_col: "CacheOccupancy", cmba_col: "CMBA", latency_col: "Latency(s)", chr_col: "CHR"})
    # Ensure iteration and Router columns exist
    if 'iteration' not in df.columns:
        # try capitalized
        if 'Iteration' in df.columns:
            df = df.rename(columns={'Iteration':'iteration'})
        else:
            raise ValueError("CSV must contain 'iteration' column")
    if 'Router' not in df.columns:
        # try other names
        if 'router' in df.columns:
            df = df.rename(columns={'router':'Router'})
        else:
            raise ValueError("CSV must contain 'Router' column")

    # compute normalized metrics + avg_score
    df_scored = compute_avg_score_per_iteration(df, col_map={'cache':'CacheOccupancy','cmba':'CMBA','latency':'Latency(s)','chr':'CHR'})
    # Add CHR and Latency columns expected in labeler
    # Convert CHR/Latency to numeric
    df_scored['CHR'] = pd.to_numeric(df_scored['CHR'], errors='coerce').astype(float)
    df_scored['Latency(s)'] = pd.to_numeric(df_scored['Latency(s)'], errors='coerce').astype(float)

    # derive labels deterministically (ground truth) from avg_score
    df_scored['label'] = 0
    recommendations_det = {}
    for it, group in df_scored.groupby('iteration', sort=True):
        best_row = group.sort_values(by=['avg_score','CHR','Latency(s)'], ascending=[False,False,True]).iloc[0]
        df_scored.loc[best_row.name, 'label'] = 1
        recommendations_det[it] = best_row['Router']

    # Prepare training set: features (CacheOccupancy, CMBA, Latency(s), CHR) + maybe avg_score
    feature_cols = ['CacheOccupancy','CMBA','Latency(s)','CHR']
    X = df_scored[feature_cols].fillna(0.0)
    y = df_scored['label'].astype(int)

    distinct_iterations = df_scored['iteration'].nunique()
    used_ensemble = False
    ensemble_scores = {}
    recommendations_ai = {}

    if SKLEARN_AVAILABLE and distinct_iterations >= min_iterations_for_training:
        # encode Router as label for per-row mapping? We train per-row binary classifier as described
        # but models require numeric features only
        X_np = X.values.astype(float)
        y_np = y.values.astype(int)
        try:
            ensemble, ensemble_scores = _train_pruned_ensemble(X_np, y_np, min_models=2, cv=3)
            if ensemble is None:
                # fallback to deterministic
                used_ensemble = False
            else:
                used_ensemble = True
                # For each iteration, predict probability for rows in that iteration and pick highest prob row
                for it, group in df_scored.groupby('iteration', sort=True):
                    Xg = group[feature_cols].fillna(0.0).values.astype(float)
                    try:
                        probs = ensemble.predict_proba(Xg)[:,1]
                        # pick index of max prob; group.index aligns with probs order
                        i_max = int(np.argmax(probs))
                        chosen_router = group.iloc[i_max]['Router']
                        recommendations_ai[it] = chosen_router
                    except Exception:
                        # if predict fails, fallback to deterministic for that iteration
                        chosen_router = recommendations_det.get(it)
                        recommendations_ai[it] = chosen_router
        except Exception as e:
            used_ensemble = False
            ensemble_scores = {'error': str(e)}
    else:
        # not enough history or sklearn not available
        used_ensemble = False
        if not SKLEARN_AVAILABLE:
            ensemble_scores['note'] = 'sklearn not available'
        else:
            ensemble_scores['note'] = f'not enough iterations for training (have {distinct_iterations})'

    # If ensemble not used, use deterministic recommendations
    if not used_ensemble:
        recommendations_ai = recommendations_det.copy()

    # Save selection history CSV
    if save_selection_history:
        os.makedirs(selection_out_dir := selection_out_dir if 'selection_out_dir' in locals() else "Path_Iterations", exist_ok=True)
        outfn = os.path.join(selection_out_dir, f"{path_name.replace(' ','_')}_selection_history.csv")
        # prepare DataFrame with iteration, path_name, ai_recommend_router, ai_used_ensemble, ai_fallback
        rows = []
        for it in sorted(df_scored['iteration'].unique()):
            rows.append({
                'iteration': int(it),
                'path_name': path_name,
                'ai_recommend_router': recommendations_ai.get(it),
                'ai_used_ensemble': bool(used_ensemble),
                'ai_fallback': (not used_ensemble)
            })
        df_sel = pd.DataFrame(rows)
        # if existing file present, append iterations that are not present
        if os.path.exists(outfn):
            existing = pd.read_csv(outfn)
            existing_iters = set(existing['iteration'].tolist())
            new_rows = [r for r in rows if r['iteration'] not in existing_iters]
            if new_rows:
                pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True).to_csv(outfn, index=False)
        else:
            df_sel.to_csv(outfn, index=False)
    else:
        outfn = None

    return {
        'selection_csv': outfn,
        'used_ensemble': bool(used_ensemble),
        'ensemble_scores': ensemble_scores,
        'recommendations_ai': recommendations_ai,
        'recommendations_det': recommendations_det
    }

import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from typing import Optional, List, Dict, Any

def plot_top_cmba_counts(path_label: str,
                         metrics_csv: Optional[str] = None,
                         path_nodes: Optional[List[str]] = None,
                         save_png: bool = True,
                         show_plot: bool = False) -> pd.DataFrame:
    """
    For each iteration, pick the router with the highest CMBA and increment its count.
    Then plot the counts as a vertical bar chart and save to Path_Iterations/plots/.

    Args:
      - path_label: label used when generating metrics CSV, e.g. "path_Router1_to_Router19"
      - metrics_csv: optional full path to metrics CSV; if None, uses Path_Iterations/{path_label}_metrics.csv
      - path_nodes: optional list of router names in path order; if provided, result/drawing will follow that order.
      - save_png: whether to save PNG file
      - show_plot: whether to call plt.show() (useful if running interactive)

    Returns:
      - DataFrame with columns ['Router','count'] sorted by path_nodes order if provided otherwise by descending count.
    """
    # determine CSV path
    if metrics_csv is None:
        # Extract just the filename part if path_label includes directory
        # Handle cases like "Path_Iterations\path_Router1_to_Router19" or just "path_Router1_to_Router19"
        path_label_clean = path_label.replace(' ', '_')
        # Remove "Path_Iterations" prefix if present
        if "Path_Iterations" in path_label_clean:
            # Extract the part after "Path_Iterations" (handle both / and \)
            if "\\" in path_label_clean or "/" in path_label_clean:
                # Split and get the last part
                parts = path_label_clean.replace("\\", "/").split("/")
                path_label_clean = parts[-1] if parts else path_label_clean
            else:
                # If it's just "Path_Iterations" without separator, use empty
                path_label_clean = ""
        # If path_label_clean is empty or just whitespace, try to extract from the original
        if not path_label_clean or path_label_clean.strip() == "":
            # Try to extract filename from path_label
            path_label_clean = os.path.splitext(os.path.basename(path_label.replace(' ', '_')))[0]
        
        # Remove .csv extension if present
        if path_label_clean.endswith('.csv'):
            path_label_clean = path_label_clean[:-4]
        
        # Try multiple naming patterns
        possible_paths = [
            os.path.join("Path_Iterations", f"{path_label_clean}_metrics.csv"),
            os.path.join("Path_Iterations", f"{path_label_clean}.csv"),
        ]
        
        metrics_csv = None
        for path in possible_paths:
            if os.path.exists(path):
                metrics_csv = path
                break
        
        if metrics_csv is None:
            raise FileNotFoundError(f"Metrics CSV not found. Tried: {possible_paths}")

    df = pd.read_csv(metrics_csv)

    # try to detect CMBA column name (common variants)
    cmba_candidates = ["CMBA","cmba","Cmba","CMBA_value"]
    cmba_col = None
    for c in cmba_candidates:
        if c in df.columns:
            cmba_col = c
            break
    if cmba_col is None:
        # fallback: try case-insensitive search
        lowmap = {col.lower(): col for col in df.columns}
        for c in cmba_candidates:
            if c.lower() in lowmap:
                cmba_col = lowmap[c.lower()]
                break
    if cmba_col is None:
        raise ValueError(f"CMBA column not found in CSV. Available columns: {list(df.columns)}")

    # Ensure iteration and Router exist
    if 'iteration' not in df.columns:
        raise ValueError("'iteration' column missing in metrics CSV")
    if 'Router' not in df.columns:
        # try lowercase
        if 'router' in df.columns:
            df = df.rename(columns={'router':'Router'})
        else:
            raise ValueError("'Router' column missing in metrics CSV")

    df['iteration'] = pd.to_numeric(df['iteration'], errors='coerce').astype(int)

    # Counting: for each iteration, pick 1 router with maximum CMBA.
    # Tie-break deterministically by Router name (alphabetical).
    counts = Counter()
    grouped = df.groupby('iteration', sort=True)
    for it, group in grouped:
        # drop NaN cmba safely
        group2 = group.copy()
        group2[cmba_col] = pd.to_numeric(group2[cmba_col], errors='coerce').astype(float)
        if group2[cmba_col].isna().all():
            # no cmba values for this iteration, skip
            continue
        # find max value
        max_val = group2[cmba_col].max()
        # select routers with max
        winners = group2[group2[cmba_col] == max_val]
        # deterministic tie-break: sort by Router name and pick first
        winners_sorted = winners.sort_values(by='Router', ascending=True)
        chosen = winners_sorted.iloc[0]['Router']
        counts[chosen] += 1

    # If path_nodes supplied, ensure all appear in final counts (zero if absent)
    if path_nodes:
        ordered_routers = list(path_nodes)
        # some path_nodes might be integers or look different: convert to str
        ordered_routers = [str(r) for r in ordered_routers]
    else:
        # order routers by descending count (for nicer plot)
        ordered_routers = [r for r, _ in counts.most_common()]

    # make DataFrame of counts
    rows = []
    # ensure we include any routers in CSV that were never chosen (count 0)
    all_routers_in_csv = list(df['Router'].unique())
    for r in ordered_routers:
        rows.append({'Router': str(r), 'count': int(counts.get(r, 0))})
    # include remaining routers (not in path_nodes or ordered list) with their counts
    for r in all_routers_in_csv:
        if r not in [row['Router'] for row in rows]:
            rows.append({'Router': str(r), 'count': int(counts.get(r, 0))})

    result_df = pd.DataFrame(rows)

    # Plot vertical bar chart similar to your sketch
    plt.figure(figsize=(max(6, 0.6 * len(result_df)), 5))
    x = range(len(result_df))
    plt.bar(x, result_df['count'], width=0.6)
    plt.xticks(x, result_df['Router'], rotation=45, ha='right')
    plt.ylabel("Number of iterations selected")
    plt.xlabel("Router")
    plt.title(f"Count of highest-CMBA router per iteration ({path_label})")
    plt.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    if save_png:
        out_dir = os.path.join("Path_Iterations", "plots")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{path_label.replace(' ','_')}_cmba_top_counts.png")
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        print(f"[plot_top_cmba_counts] saved plot -> {out_path}")

    if show_plot:
        plt.show()
    plt.close()

    return result_df

def explain_router_recommendation(csv_path: str, 
                                  iteration: int = 1,
                                  top_n: int = 5) -> pd.DataFrame:
    """
    Explain why a router was selected as the best for caching.
    Shows detailed metrics comparison for all routers.
    
    Args:
        csv_path: Path to metrics CSV file
        iteration: Iteration number to analyze
        top_n: Number of top routers to show in detail
    
    Returns:
        DataFrame with detailed explanation and metrics
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Detect and standardize columns
    cache_col = _detect_column(df, ["CacheOccupancy", "Cache Occupy", "Cache occupy", "CacheOccupy"])
    cmba_col = _detect_column(df, ["CMBA", "cmba", "Cmba"])
    latency_col = _detect_column(df, ["Latency_ms", "Latency(s)", "Latency", "latency_ms"])
    chr_col = _detect_column(df, ["CHR", "Chr", "CHR%", "Cache Hit Ratio"])
    
    if any(c is None for c in [cache_col, cmba_col, latency_col, chr_col]):
        raise ValueError(f"Could not detect required columns. Found: {list(df.columns)}")
    
    df = df.rename(columns={
        cache_col: "CacheOccupancy",
        cmba_col: "CMBA",
        latency_col: "Latency(s)",
        chr_col: "CHR"
    })
    
    # Ensure iteration column exists
    if 'iteration' not in df.columns:
        if 'Iteration' in df.columns:
            df = df.rename(columns={'Iteration': 'iteration'})
        else:
            raise ValueError("CSV must contain 'iteration' column")
    
    # Filter for the specified iteration
    df_iter = df[df['iteration'] == iteration].copy()
    if df_iter.empty:
        raise ValueError(f"No data found for iteration {iteration}")
    
    # Compute scores
    df_scored = compute_avg_score_per_iteration(
        df_iter,
        col_map={'cache': 'CacheOccupancy', 'cmba': 'CMBA', 
                'latency': 'Latency(s)', 'chr': 'CHR'}
    )
    
    # Sort by avg_score descending
    df_scored = df_scored.sort_values('avg_score', ascending=False).reset_index(drop=True)
    
    # Get best router
    best_router = df_scored.iloc[0]
    
    # Create explanation DataFrame
    explanation_data = []
    for idx, row in df_scored.iterrows():
        explanation_data.append({
            'Rank': idx + 1,
            'Router': row['Router'],
            'CMBA': f"{row['CMBA']:.4f}",
            'CHR (%)': f"{row['CHR']:.2f}",
            'Cache Occupancy': f"{row['CacheOccupancy']:.2f}",
            'Latency (s)': f"{row['Latency(s)']:.4f}",
            'Normalized CMBA': f"{row['norm_CMBA']:.4f}",
            'Normalized CHR': f"{row['norm_CHR']:.4f}",
            'Normalized Cache': f"{row['norm_Cache']:.4f}",
            'Normalized Latency': f"{row['norm_Latency']:.4f}",
            'Average Score': f"{row['avg_score']:.4f}",
            'Selected': '[BEST]' if idx == 0 else ''
        })
    
    explanation_df = pd.DataFrame(explanation_data)
    
    return explanation_df, best_router

def recommend_best_router_for_network(routers: Optional[List[Any]] = None,
                                      network_metrics_csv: Optional[str] = None,
                                      iteration: int = 1,
                                      min_iterations_for_training: int = 3,
                                      save_history: bool = True) -> Dict[str, Any]:
    """
    Recommend the best router for caching data across the entire network/graph.
    
    This function analyzes all routers in the network (not just a specific path) and
    recommends the best router to cache data based on multiple metrics.
    
    Args:
        routers: List of Router objects from the network. If None, will try to load from network_metrics_csv.
        network_metrics_csv: Optional path to CSV file with network-wide router metrics.
                            Expected columns: iteration, Router, CacheOccupancy/Cache occupy, CMBA, Latency(s), CHR
        iteration: Current iteration number (default: 1)
        min_iterations_for_training: Minimum iterations needed to train ensemble (default: 3)
        save_history: Whether to save recommendation history (default: True)
    
    Returns:
        Dictionary with:
        - 'recommended_router': Best router name for caching
        - 'confidence': Confidence score (probability from ensemble)
        - 'used_ensemble': Whether ML ensemble was used
        - 'ensemble_scores': Model performance scores
        - 'all_router_scores': DataFrame with scores for all routers
        - 'history_csv': Path to saved history file
    """
    # Collect metrics for all routers
    if routers is not None:
        # Extract metrics from router objects
        router_data = []
        for router in routers:
            # Get cache occupancy
            cache_occupy = len(getattr(router, 'cs', [])) / getattr(router, 'CACHE_LIMIT', 15)
            
            # Get CHR (Cache Hit Ratio)
            total_requests = getattr(router, 'total_requests', 0)
            cache_hits = getattr(router, 'cache_hits', 0)
            chr_val = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0
            
            # Get latency (using total_cache_access_time / requests)
            total_access_time = getattr(router, 'total_cache_access_time', 0.0)
            latency = (total_access_time / total_requests) if total_requests > 0 else 0.0
            
            # Get CMBA - try to get from router attributes or calculate
            cmba = getattr(router, 'cmba', 0.0)
            if cmba == 0.0:
                # Try to get from centrality metrics if available
                try:
                    from main import plot_centrality_measures
                    # This will compute and save CMBA
                    plot_centrality_measures([router], save_path=None, show_plot=False)
                    # Read from saved file
                    cmba_file = "Graphs/Centrality/cmba.csv"
                    if os.path.exists(cmba_file):
                        df_cmba = pd.read_csv(cmba_file)
                        router_cmba = df_cmba[df_cmba['Router'] == router.name]
                        if not router_cmba.empty:
                            cmba = float(router_cmba['CMBA'].iloc[0])
                except Exception:
                    cmba = 0.0
            
            router_data.append({
                'iteration': iteration,
                'Router': router.name,
                'Cache occupy': cache_occupy,
                'CMBA': cmba,
                'Latency(s)': latency,
                'CHR': chr_val
            })
        
        # Create DataFrame from router data
        df = pd.DataFrame(router_data)
        
        # Save to temporary CSV for processing
        temp_csv = os.path.join("Path_Iterations", f"network_iteration_{iteration}_temp.csv")
        os.makedirs("Path_Iterations", exist_ok=True)
        df.to_csv(temp_csv, index=False)
        csv_path = temp_csv
        path_name = "network_wide"
        
    elif network_metrics_csv is not None:
        if not os.path.exists(network_metrics_csv):
            raise FileNotFoundError(f"Network metrics CSV not found: {network_metrics_csv}")
        csv_path = network_metrics_csv
        path_name = os.path.splitext(os.path.basename(network_metrics_csv))[0]
    else:
        raise ValueError("Either 'routers' or 'network_metrics_csv' must be provided")
    
    # Use existing generate_ai_recommendations function
    try:
        result = generate_ai_recommendations(
            csv_path=csv_path,
            path_name=path_name,
            min_iterations_for_training=min_iterations_for_training,
            save_selection_history=save_history
        )
        
        # Get the best router for current iteration
        if iteration in result['recommendations_ai']:
            recommended_router = result['recommendations_ai'][iteration]
        else:
            # If iteration not in recommendations, get the most recent or best overall
            if result['recommendations_ai']:
                recommended_router = list(result['recommendations_ai'].values())[-1]
            else:
                # Fallback: use deterministic recommendation
                recommended_router = result['recommendations_det'].get(iteration, None)
        
        # Read the scored data to get confidence scores
        df_scored = pd.read_csv(csv_path)
        if 'avg_score' not in df_scored.columns:
            # Compute scores if not present
            cache_col = _detect_column(df_scored, ["CacheOccupancy", "Cache Occupy", "Cache occupy"])
            cmba_col = _detect_column(df_scored, ["CMBA", "cmba"])
            latency_col = _detect_column(df_scored, ["Latency_ms", "Latency(s)", "Latency"])
            chr_col = _detect_column(df_scored, ["CHR", "Chr", "CHR%"])
            
            if all(c is not None for c in [cache_col, cmba_col, latency_col, chr_col]):
                df_scored = df_scored.rename(columns={
                    cache_col: "CacheOccupancy",
                    cmba_col: "CMBA",
                    latency_col: "Latency(s)",
                    chr_col: "CHR"
                })
                df_scored = compute_avg_score_per_iteration(
                    df_scored,
                    col_map={'cache': 'CacheOccupancy', 'cmba': 'CMBA',
                            'latency': 'Latency(s)', 'chr': 'CHR'}
                )
        
        # Get confidence (avg_score of recommended router)
        if recommended_router:
            router_row = df_scored[df_scored['Router'] == recommended_router]
            if not router_row.empty and 'avg_score' in router_row.columns:
                confidence = float(router_row['avg_score'].iloc[0])
            else:
                confidence = 0.0
        else:
            confidence = 0.0
        
        # Clean up temp file if created
        if routers is not None and os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except Exception:
                pass
        
        return {
            'recommended_router': recommended_router,
            'confidence': confidence,
            'used_ensemble': result['used_ensemble'],
            'ensemble_scores': result['ensemble_scores'],
            'all_router_scores': df_scored[['Router', 'avg_score']].sort_values('avg_score', ascending=False) if 'avg_score' in df_scored.columns else pd.DataFrame(),
            'history_csv': result['selection_csv'],
            'all_recommendations': result['recommendations_ai']
        }
        
    except Exception as e:
        # Clean up temp file on error
        if routers is not None and 'temp_csv' in locals() and os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except Exception:
                pass
        raise


# If run directly, quick demo with file path argument
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("csv_path", nargs='?', default=r"Path_Iterations\path_Router1_to_Router19.csv", 
                   help="path to metrics CSV e.g. Path_Iterations/path_Router1_to_Router19.csv (default: Path_Iterations/path_Router1_to_Router19.csv)")
    p.add_argument("--path_name", default=None, help="path label to use for output files (optional)")
    p.add_argument("--min_iters", type=int, default=8, help="min iterations to try training")
    p.add_argument("--explain", action='store_true', help="show detailed explanation of router selection")
    p.add_argument("--iteration", type=int, default=1, help="iteration to explain (used with --explain)")
    args = p.parse_args()
    if not args.path_name:
        args.path_name = os.path.splitext(os.path.basename(args.csv_path))[0]
    
    if args.explain:
        # Show detailed explanation
        print("=" * 80)
        print("ROUTER SELECTION EXPLANATION")
        print("=" * 80)
        try:
            explanation_df, best_router = explain_router_recommendation(args.csv_path, args.iteration)
            print(f"\n[Analysis for Iteration {args.iteration}]")
            print(f"BEST ROUTER: {best_router['Router']}")
            print(f"   Average Score: {best_router['avg_score']:.4f}")
            print(f"\nDetailed Metrics Comparison:")
            print(explanation_df.to_string(index=False))
            print("\n" + "=" * 80)
            print("HOW THE SELECTION WORKS:")
            print("=" * 80)
            print("1. Metrics are normalized per iteration (0-1 scale)")
            print("2. CMBA & CHR: Higher is better -> normalized directly")
            print("3. Cache Occupancy & Latency: Lower is better -> normalized inversely")
            print("4. Average Score = mean(norm_CMBA, norm_CHR, norm_Cache, norm_Latency)")
            print("5. Router with HIGHEST average score is selected")
            print("=" * 80)
        except Exception as e:
            print(f"Error generating explanation: {e}")
    else:
        # Normal recommendation
        res = generate_ai_recommendations(args.csv_path, args.path_name, min_iterations_for_training=args.min_iters)
        print("Results summary:")
        print(" selection_csv:", res['selection_csv'])
        print(" used_ensemble:", res['used_ensemble'])
        print(" ensemble_scores:", res['ensemble_scores'])
        print(" sample recommendations (first 5):", dict(list(res['recommendations_ai'].items())[:5]))
        print("\nTip: Use --explain flag to see detailed metrics comparison")
        print("   Example: python ai_recommender.py --explain --iteration 1")
