# ai_network_recommender.py
"""
Network-wide metric collection + equal-weight scoring + multiclass RF trainer.

Outputs:
 - CSV: Path_Iterations/network_metrics.csv  (iteration, Router, CacheOccupancy, CacheOccupancyPct, CMBA, Latency_ms, CHR)
 - CSV: Path_Iterations/network_selection_history.csv (iteration, best_by_score, best_by_model, model_used)
 - Returns DataFrames for metrics and selection history.

Usage:
    from ai_network_recommender import collect_network_metrics, equal_weight_select_and_train

    # after you have router objects list `routers` (from main.setup_network())
    metrics_csv = collect_network_metrics(routers, n_iterations=20, out_csv="Path_Iterations/network_metrics.csv")
    res = equal_weight_select_and_train(metrics_csv, selection_out="Path_Iterations/network_selection_history.csv",
                                        min_iters_for_training=8)
"""
import os
if os.path.exists("Path_Iterations/network_metrics.csv"):
    os.remove("Path_Iterations/network_metrics.csv")
import math
import random
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

# sklearn optional

try:
    from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier, VotingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import LabelEncoder
    SKLEARN = True
except Exception:
    SKLEARN = False



CSV_DIR = "Path_Iterations"
PLOT_DIR = os.path.join(CSV_DIR, "plots")
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)


def _safe_div(a, b):
    try:
        if b is None or b == 0:
            return float('nan')
        return float(a) / float(b)
    except Exception:
        return float('nan')


def _read_router_metrics(router) -> Dict[str, Any]:
    """
    Extract canonical metrics from a Router object.
    Expects router to have attributes:
      - name (string)
      - cs (list or iterable)  -> CacheOccupancy = len(cs)
      - class attribute CACHE_LIMIT
      - cache_hits, total_requests
      - total_cache_access_time (seconds) OR avg_cache_latency_ms
      - CMBA (float) maybe precomputed
    Returns a dict with keys CacheOccupancy, CACHE_LIMIT, CMBA, Latency_ms, CHR
    """
    out = {
        "CacheOccupancy": None,
        "CACHE_LIMIT": None,
        "CMBA": float('nan'),
        "Latency_ms": float('nan'),
        "CHR": float('nan')
    }
    if router is None:
        return out
    # occupancy
    cs = getattr(router, "cs", None)
    try:
        out["CacheOccupancy"] = int(len(cs)) if cs is not None else None
    except Exception:
        out["CacheOccupancy"] = None
    # cap
    cap = getattr(router.__class__, "CACHE_LIMIT", None)
    if cap is None:
        cap = getattr(router, "CACHE_LIMIT", None)
    out["CACHE_LIMIT"] = cap
    # CMBA
    cmba = getattr(router, "CMBA", None)
    if cmba is not None:
        try:
            out["CMBA"] = float(cmba)
        except Exception:
            out["CMBA"] = float('nan')
    # CHR
    ch = getattr(router, "cache_hits", None)
    tr = getattr(router, "total_requests", None)
    out["CHR"] = _safe_div(ch, tr) if tr is not None else float('nan')
    # Latency
    tcat = getattr(router, "total_cache_access_time", None)
    if tr and tr > 0 and tcat is not None:
        out["Latency_ms"] = float(tcat) / float(tr) * 1000.0
    else:
        alt = getattr(router, "avg_cache_latency_ms", None)
        if alt is not None:
            try:
                out["Latency_ms"] = float(alt)
            except Exception:
                out["Latency_ms"] = float('nan')
    return out


def collect_network_metrics(routers: List[Any],
                            n_iterations: int = 100,
                            perturb: bool = True,
                            out_csv: str = None) -> str:
    """
    Collect metrics for ALL routers in `routers` for n_iterations.
    routers: list of Router objects (must have .name)
    Outputs CSV with columns:
      iteration, Router, CacheOccupancy, CacheOccupancyPct, CMBA, Latency_ms, CHR
    Returns path to CSV (out_csv)
    """
    if out_csv is None:
        out_csv = os.path.join(CSV_DIR, "network_metrics.csv")

    records = []
    # build router map
    rmap = {getattr(r, "name", str(r)): r for r in routers}

    for it in range(1, n_iterations + 1):
        for name, robj in rmap.items():
            m = _read_router_metrics(robj)
            # if runtime values are missing, fill with random sensible defaults to keep dataset consistent
            if m["CacheOccupancy"] is None:
                m["CacheOccupancy"] = random.randint(0, 30)
            if m["CACHE_LIMIT"] is None:
                m["CACHE_LIMIT"] = getattr(robj.__class__, "CACHE_LIMIT", 50) if robj is not None else 50
            if math.isnan(m["CMBA"]):
                # try attribute name cmba lower-case or compute placeholder
                val = getattr(robj, "cmba", None) if robj is not None else None
                m["CMBA"] = float(val) if val is not None else round(random.uniform(0.1, 10.0), 4)
            if math.isnan(m["CHR"]):
                m["CHR"] = round(random.uniform(0.0, 1.0), 4)
            if math.isnan(m["Latency_ms"]):
                m["Latency_ms"] = round(random.uniform(1.0, 300.0), 4)

            occ_pct = (m["CacheOccupancy"] / m["CACHE_LIMIT"] * 100.0) if (m["CACHE_LIMIT"] and m["CACHE_LIMIT"] > 0) else float('nan')

            # optionally perturb to emulate dynamics (small jitter)
            if perturb:
                m["CacheOccupancy"] = max(0, int(m["CacheOccupancy"] + random.randint(-1, 1)))
                m["CMBA"] = round(m["CMBA"] * (1 + random.uniform(-0.03, 0.03)), 6) if not math.isnan(m["CMBA"]) else m["CMBA"]
                m["Latency_ms"] = round(m["Latency_ms"] * (1 + random.uniform(-0.05, 0.05)), 6) if not math.isnan(m["Latency_ms"]) else m["Latency_ms"]
                if not math.isnan(m["CHR"]):
                    m["CHR"] = round(min(1.0, max(0.0, m["CHR"] + random.uniform(-0.02, 0.02))), 6)

                occ_pct = (m["CacheOccupancy"] / m["CACHE_LIMIT"] * 100.0) if (m["CACHE_LIMIT"] and m["CACHE_LIMIT"] > 0) else float('nan')

            records.append({
                "iteration": int(it),
                "Router": str(name),
                "CacheOccupancy": int(m["CacheOccupancy"]),
                "CacheOccupancyPct": round(occ_pct, 4) if not math.isnan(occ_pct) else float('nan'),
                "CMBA": float(m["CMBA"]),
                "Latency_ms": float(m["Latency_ms"]),
                "CHR": float(m["CHR"])
            })

    df = pd.DataFrame(records, columns=["iteration","Router","CacheOccupancy","CacheOccupancyPct","CMBA","Latency_ms","CHR"])
    df.to_csv(out_csv, index=False)
    print(f"[collect_network_metrics] Saved {len(df)} rows to {out_csv}")
    return out_csv


def _normalize_per_iteration(df: pd.DataFrame, col: str, higher_is_better: bool) -> pd.Series:
    s = pd.to_numeric(df[col], errors='coerce').astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0]*len(s), index=s.index)
    if higher_is_better:
        return (s - mn) / (mx - mn)
    else:
        return (mx - s) / (mx - mn)


def equal_weight_select_and_train(metrics_csv: str=r"Path_Iterations/network_metrics.csv",
                                  selection_out: str = None,
                                  min_iters_for_training: int = 8) -> Dict[str, Any]:
    """
    1) Reads metrics_csv (network_metrics.csv)
    2) For each iteration, normalize four features per-iteration and compute avg_score with equal weights.
       - CMBA (benefit), CHR (benefit), Latency_ms (cost), CacheOccupancy (cost)
    3) Choose best_by_score router per iteration (deterministic).
    4) If enough distinct iterations and sklearn available, train a multiclass RandomForest to predict best router.
       Produces predictions per iteration (best_by_model).
    5) Saves selection history CSV with columns: iteration, best_by_score, best_by_model, model_used
    Returns dict with dataframes and model info.
    """
    if not os.path.exists(metrics_csv):
        raise FileNotFoundError(metrics_csv)
    df = pd.read_csv(metrics_csv)
    # check columns
    required = ['iteration','Router','CacheOccupancy','CMBA','Latency_ms','CHR']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"metrics CSV missing required column: {c}")

    # normalize per-iteration
    df_sorted = df.sort_values(['iteration','Router']).reset_index(drop=True)
    normalized = []
    for it, group in df_sorted.groupby('iteration', sort=True):
        g = group.copy().reset_index(drop=True)
        g['n_CMBA'] = _normalize_per_iteration(g, 'CMBA', higher_is_better=True)
        g['n_CHR'] = _normalize_per_iteration(g, 'CHR', higher_is_better=True)
        g['n_Latency'] = _normalize_per_iteration(g, 'Latency_ms', higher_is_better=False)
        g['n_CacheOcc'] = _normalize_per_iteration(g, 'CacheOccupancy', higher_is_better=False)
        # equal weights -> average
        g['avg_score_eq'] = g[['n_CMBA','n_CHR','n_Latency','n_CacheOcc']].mean(axis=1)
        normalized.append(g)
    df_norm = pd.concat(normalized, ignore_index=True)

    # determine best_by_score per iteration
    # Note: Lower cache occupancy is better (already normalized), so routers with 0 occupancy are preferred
    best_by_score = {}
    for it, group in df_norm.groupby('iteration', sort=True):
        # choose max avg_score_eq, break ties by CHR desc then Latency asc then Router name
        # The normalization already favors lower cache occupancy, so empty routers (0 occupancy) score higher
        sel = group.sort_values(by=['avg_score_eq','CHR','Latency_ms','Router'], ascending=[False,False,True,True]).iloc[0]
        best_by_score[it] = sel['Router']
    # attach to df_norm for training labels
    df_norm['best_by_score'] = df_norm['iteration'].map(best_by_score)
    df_norm['label_is_best'] = (df_norm['Router'] == df_norm['best_by_score']).astype(int)
    
    # Create AI-optimized label: balance CHR, latency, and cache occupancy
    # This allows AI to learn patterns that optimize for actual performance, not just replicate deterministic
    # Weight: CHR (30%), CMBA (20%), Latency (30%), CacheOcc (20%) - balanced approach
    # Note: n_CacheOcc is higher for lower occupancy (good), so this favors empty routers
    df_norm['ai_performance_score'] = (
        df_norm['n_CHR'] * 0.30 +      # CHR is important for caching
        df_norm['n_CMBA'] * 0.20 +     # CMBA is important
        df_norm['n_Latency'] * 0.30 +  # Low latency is critical (increased weight)
        df_norm['n_CacheOcc'] * 0.20   # Low cache occupancy is good (increased weight)
    )
    # Label routers with top ai_performance_score in each iteration as "best" for AI training
    df_norm['label_is_best_ai'] = 0
    for it, group in df_norm.groupby('iteration', sort=True):
        best_ai_idx = group['ai_performance_score'].idxmax()
        df_norm.loc[best_ai_idx, 'label_is_best_ai'] = 1

    # produce selection_history DataFrame for deterministic selection
    selection_rows = []
    for it in sorted(df_norm['iteration'].unique()):
        selection_rows.append({'iteration': int(it), 'best_by_score': best_by_score[it]})
    selection_df = pd.DataFrame(selection_rows)

    # Try training binary classifier: predict if a router row is the best (1) or not (0)
    distinct_iters = df_norm['iteration'].nunique()
    model_used = False
    model = None
    predictions = {}  # iteration -> predicted router
    if SKLEARN and distinct_iters >= min_iters_for_training:
        try:
            # Training: binary classification - use performance-based labels that prioritize CHR and latency
            # This allows AI to learn patterns that optimize for actual performance metrics, not just replicate deterministic
            feature_cols = ['CacheOccupancy','CMBA','Latency_ms','CHR']
            X = df_norm[feature_cols].fillna(0.0).values.astype(float)
            # Use AI-optimized labels (emphasizes CHR and latency) instead of deterministic labels
            # This trains the model to optimize for actual performance metrics
            y = df_norm['label_is_best_ai'].values.astype(int)
            
            # If all labels are 0 (shouldn't happen), fall back to deterministic labels
            if y.sum() == 0:
                print("[equal_weight_select_and_train] Warning: performance labels all zero, using deterministic labels")
                y = df_norm['label_is_best'].values.astype(int)
            
            # Train ensemble of classifiers (same as ai_recommender.py)
            from sklearn.model_selection import cross_val_score
            models = [
                ('rf', RandomForestClassifier(n_estimators=200, random_state=42)),
                ('et', ExtraTreesClassifier(n_estimators=200, random_state=42)),
                ('gb', GradientBoostingClassifier(n_estimators=200, random_state=42))
            ]
            scores = {}
            cv_use = max(2, min(3, len(y))) if len(y) >= 2 else 2
            for name, m in models:
                try:
                    sc = cross_val_score(m, X, y, cv=cv_use, scoring='accuracy')
                    scores[name] = float(np.mean(sc))
                except Exception:
                    scores[name] = 0.0
            
            mean_score = np.mean(list(scores.values())) if scores else 0.0
            threshold = max(0.5, mean_score)
            kept = [m for (n,m) in models if scores.get(n,0.0) >= threshold]
            if len(kept) < 2:
                sorted_models = sorted(models, key=lambda nm: scores.get(nm[0],0.0), reverse=True)
                kept = [m for (_,m) in sorted_models[:2]]
            
            # Fit kept models and create voting classifier
            fitted = []
            for m in kept:
                m.fit(X, y)
                fitted.append((type(m).__name__, m))
            
            if fitted:
                vc = VotingClassifier(estimators=fitted, voting='soft')
                vc.fit(X, y)
                model = vc
                model_used = True
                
                # Predict per iteration: for each iteration, get probability that each router is best
                # Note: Lower cache occupancy is better (already in training), so routers with 0 occupancy are preferred
                for it, group in df_norm.groupby('iteration', sort=True):
                    Xg = group[feature_cols].fillna(0.0).values.astype(float)
                    # Get probability that each router row is the best (class 1)
                    probs = vc.predict_proba(Xg)[:,1]  # probability of being best
                    # Pick router with highest probability
                    best_idx = int(np.argmax(probs))
                    predicted_router = group.iloc[best_idx]['Router']
                    predictions[it] = predicted_router
            else:
                model_used = False
                model = None
                predictions = {}
        except Exception as e:
            model_used = False
            model = None
            predictions = {}
            print("[equal_weight_select_and_train] training failed, falling back to deterministic. Error:", e)
            import traceback
            traceback.print_exc()
    else:
        model_used = False

    # If model not used, fallback predictions = deterministic best_by_score
    if not model_used:
        for it in best_by_score:
            predictions[it] = best_by_score[it]

    # Save selection history CSV
    select_out = selection_out if selection_out is not None else os.path.join(CSV_DIR, "network_selection_history.csv")
    selrows = []
    for it in sorted(predictions.keys()):
        selrows.append({
            "iteration": int(it),
            "best_by_model": predictions[it],
            "model_used": bool(model_used)
        })
    pd.DataFrame(selrows).to_csv(select_out, index=False)
    print(f"[equal_weight_select_and_train] Saved selection history to {select_out}")

    return {
        "metrics_df": df_norm,
        "selection_df": pd.DataFrame(selrows),
        "model_used": bool(model_used),
        "model": model
    }


# Example quick-run if module executed directly (demo)
if __name__ == "__main__":
    print("Demo run (no real Router objects available) — synthetic network of 8 fake routers")
    class FakeRouter:
        def __init__(self, name):
            self.name = name
            self.cs = [i for i in range(random.randint(0, 20))]
            self.cache_hits = random.randint(0, 100)
            self.total_requests = random.randint(1, 200)
            self.total_cache_access_time = random.uniform(0.1, 20.0)
            self.CMBA = random.uniform(0.1, 8.0)
            self.CACHE_LIMIT = 50

    fr = [FakeRouter(f"Router{i}") for i in range(1, 9)]
    csv_path = collect_network_metrics(fr, n_iterations=12, perturb=True, out_csv=os.path.join(CSV_DIR,"network_demo_metrics.csv"))
    res = equal_weight_select_and_train(csv_path, selection_out=os.path.join(CSV_DIR,"network_demo_selection.csv"), min_iters_for_training=6)
    print("Done. model_used:", res['model_used'])
