# ai_network_recommender_enhanced.py
"""
Enhanced AI Network Recommender with Advanced ML/DL Ensemble
- Includes XGBoost, LightGBM, Neural Network in addition to existing models
- Tracks comprehensive metrics: CHR, Latency, Hop Reduction, Detection Cost, Prediction Time, Accuracy
- Provides detailed performance analysis and plotting
"""

import os
import time
import math
import random
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# sklearn imports
try:
    from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier, VotingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.neural_network import MLPClassifier
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN = True
except Exception:
    SKLEARN = False

# Advanced ML libraries (optional)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except Exception:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except Exception:
    LIGHTGBM_AVAILABLE = False

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
    """Extract canonical metrics from a Router object."""
    out = {
        "CacheOccupancy": None,
        "CACHE_LIMIT": None,
        "CMBA": float('nan'),
        "Latency_ms": float('nan'),
        "CHR": float('nan')
    }
    if router is None:
        return out
    
    cs = getattr(router, "cs", None)
    try:
        out["CacheOccupancy"] = int(len(cs)) if cs is not None else None
    except Exception:
        out["CacheOccupancy"] = None
    
    cap = getattr(router.__class__, "CACHE_LIMIT", None)
    if cap is None:
        cap = getattr(router, "CACHE_LIMIT", None)
    out["CACHE_LIMIT"] = cap
    
    cmba = getattr(router, "CMBA", None)
    if cmba is not None:
        try:
            out["CMBA"] = float(cmba)
        except Exception:
            out["CMBA"] = float('nan')
    
    ch = getattr(router, "cache_hits", None)
    tr = getattr(router, "total_requests", None)
    out["CHR"] = _safe_div(ch, tr) if tr is not None else float('nan')
    
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
    """Collect metrics for ALL routers in `routers` for n_iterations."""
    if out_csv is None:
        out_csv = os.path.join(CSV_DIR, "network_metrics.csv")

    records = []
    rmap = {getattr(r, "name", str(r)): r for r in routers}

    for it in range(1, n_iterations + 1):
        for name, robj in rmap.items():
            m = _read_router_metrics(robj)
            
            if m["CacheOccupancy"] is None:
                m["CacheOccupancy"] = random.randint(0, 30)
            if m["CACHE_LIMIT"] is None:
                m["CACHE_LIMIT"] = getattr(robj.__class__, "CACHE_LIMIT", 50) if robj is not None else 50
            if math.isnan(m["CMBA"]):
                val = getattr(robj, "cmba", None) if robj is not None else None
                m["CMBA"] = float(val) if val is not None else round(random.uniform(0.1, 10.0), 4)
            if math.isnan(m["CHR"]):
                m["CHR"] = round(random.uniform(0.0, 1.0), 4)
            if math.isnan(m["Latency_ms"]):
                m["Latency_ms"] = round(random.uniform(1.0, 300.0), 4)

            occ_pct = (m["CacheOccupancy"] / m["CACHE_LIMIT"] * 100.0) if (m["CACHE_LIMIT"] and m["CACHE_LIMIT"] > 0) else float('nan')

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


def calculate_hop_reduction(selected_router: str, routers: List[Any], 
                           df_norm: pd.DataFrame = None, iteration: int = None) -> float:
    """
    Calculate hop reduction achieved by selecting a cache router.
    Hop reduction = (original_hops - actual_hops) / original_hops
    
    Uses CMBA and network position to estimate hop reduction.
    Higher CMBA and better centrality = more hop reduction.
    """
    # If we have dataframe with metrics, use that
    if df_norm is not None and iteration is not None:
        router_data = df_norm[(df_norm['Router'] == selected_router) & 
                             (df_norm['iteration'] == iteration)]
        if not router_data.empty:
            cmba = router_data['CMBA'].iloc[0]
            chr_val = router_data['CHR'].iloc[0]
            # Estimate hop reduction based on CMBA (centrality) and CHR (cache effectiveness)
            # Higher CMBA = better network position = more hop reduction
            # Higher CHR = better cache = more hop reduction
            # Normalize CMBA (assuming range 0-10) and combine with CHR
            cmba_normalized = min(1.0, max(0.0, cmba / 10.0))
            hop_reduction = (cmba_normalized * 0.6 + chr_val * 0.4)  # Weighted combination
            return hop_reduction
    
    # Fallback: try to get from router object
    router_obj = next((r for r in routers if getattr(r, "name", str(r)) == selected_router), None)
    if router_obj:
        cmba = getattr(router_obj, "CMBA", 0.0)
        chr_val = getattr(router_obj, "cache_hits", 0) / max(1, getattr(router_obj, "total_requests", 1))
        cmba_normalized = min(1.0, max(0.0, cmba / 10.0))
        hop_reduction = (cmba_normalized * 0.6 + chr_val * 0.4)
        return hop_reduction
    
    return 0.0


def enhanced_ensemble_train_and_predict(metrics_csv: str = r"Path_Iterations/network_metrics.csv",
                                        selection_out: str = None,
                                        min_iters_for_training: int = 8,
                                        routers: List[Any] = None) -> Dict[str, Any]:
    """
    Enhanced ensemble with XGBoost, LightGBM, Neural Network + existing models.
    Tracks comprehensive metrics: CHR, Latency, Hop Reduction, Detection Cost, Prediction Time, Accuracy.
    """
    if not os.path.exists(metrics_csv):
        raise FileNotFoundError(metrics_csv)
    df = pd.read_csv(metrics_csv)
    
    required = ['iteration','Router','CacheOccupancy','CMBA','Latency_ms','CHR']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"metrics CSV missing required column: {c}")

    # Normalize per-iteration
    df_sorted = df.sort_values(['iteration','Router']).reset_index(drop=True)
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

    # Determine best_by_score per iteration (ICN baseline)
    best_by_score = {}
    for it, group in df_norm.groupby('iteration', sort=True):
        sel = group.sort_values(by=['avg_score_eq','CHR','Latency_ms','Router'], 
                               ascending=[False,False,True,True]).iloc[0]
        best_by_score[it] = sel['Router']
    
    df_norm['best_by_score'] = df_norm['iteration'].map(best_by_score)
    df_norm['label_is_best'] = (df_norm['Router'] == df_norm['best_by_score']).astype(int)
    
    # AI-optimized labels
    df_norm['ai_performance_score'] = (
        df_norm['n_CHR'] * 0.30 +
        df_norm['n_CMBA'] * 0.20 +
        df_norm['n_Latency'] * 0.30 +
        df_norm['n_CacheOcc'] * 0.20
    )
    df_norm['label_is_best_ai'] = 0
    for it, group in df_norm.groupby('iteration', sort=True):
        best_ai_idx = group['ai_performance_score'].idxmax()
        df_norm.loc[best_ai_idx, 'label_is_best_ai'] = 1

    # Metrics tracking
    metrics_tracking = {
        'iteration': [],
        'CHR': [],
        'Latency': [],
        'HopReduction': [],
        'DetectionCost': [],
        'PredictionTime': [],
        'Accuracy': []
    }

    # Enhanced ensemble training
    distinct_iters = df_norm['iteration'].nunique()
    model_used = False
    model = None
    predictions = {}
    model_components = []
    
    if SKLEARN and distinct_iters >= min_iters_for_training:
        try:
            feature_cols = ['CacheOccupancy','CMBA','Latency_ms','CHR']
            X = df_norm[feature_cols].fillna(0.0).values.astype(float)
            y = df_norm['label_is_best_ai'].values.astype(int)
            
            if y.sum() == 0:
                print("[enhanced_ensemble] Warning: performance labels all zero, using deterministic labels")
                y = df_norm['label_is_best'].values.astype(int)
            
            # Build enhanced ensemble
            models = []
            
            # Base models
            models.append(('rf', RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)))
            models.append(('et', ExtraTreesClassifier(n_estimators=200, random_state=42, n_jobs=-1)))
            models.append(('gb', GradientBoostingClassifier(n_estimators=200, random_state=42)))
            
            # Advanced models (if available)
            if XGBOOST_AVAILABLE:
                models.append(('xgb', xgb.XGBClassifier(n_estimators=200, random_state=42, n_jobs=-1, eval_metric='logloss')))
            
            if LIGHTGBM_AVAILABLE:
                models.append(('lgb', lgb.LGBMClassifier(n_estimators=200, random_state=42, n_jobs=-1, verbose=-1)))
            
            # Neural Network
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            models.append(('nn', MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42, early_stopping=True)))
            
            # Evaluate models
            scores = {}
            cv_use = max(2, min(3, len(y))) if len(y) >= 2 else 2
            for name, m in models:
                try:
                    if name == 'nn':
                        sc = cross_val_score(m, X_scaled, y, cv=cv_use, scoring='accuracy')
                    else:
                        sc = cross_val_score(m, X, y, cv=cv_use, scoring='accuracy')
                    scores[name] = float(np.mean(sc))
                    print(f"[enhanced_ensemble] {name} CV accuracy: {scores[name]:.4f}")
                except Exception as e:
                    scores[name] = 0.0
                    print(f"[enhanced_ensemble] {name} failed: {e}")
            
            # Select top models (keep those with score >= mean or top 4)
            mean_score = np.mean(list(scores.values())) if scores else 0.0
            threshold = max(0.5, mean_score * 0.9)  # Keep models within 90% of mean
            kept = [(n, m) for (n, m) in models if scores.get(n, 0.0) >= threshold]
            
            if len(kept) < 2:
                sorted_models = sorted(models, key=lambda nm: scores.get(nm[0], 0.0), reverse=True)
                kept = sorted_models[:min(4, len(sorted_models))]
            
            # Fit kept models
            fitted = []
            for name, m in kept:
                try:
                    if name == 'nn':
                        m.fit(X_scaled, y)
                    else:
                        m.fit(X, y)
                    fitted.append((name, m))
                    model_components.append(name)
                    print(f"[enhanced_ensemble] Fitted {name}")
                except Exception as e:
                    print(f"[enhanced_ensemble] Failed to fit {name}: {e}")
            
            if fitted:
                # Create voting classifier
                vc = VotingClassifier(estimators=fitted, voting='soft')
                if any(n == 'nn' for n, _ in fitted):
                    # If NN is in ensemble, need to scale for predictions
                    vc.fit(X_scaled, y)
                    model = (vc, scaler, True)  # (model, scaler, needs_scaling)
                else:
                    vc.fit(X, y)
                    model = (vc, None, False)
                
                model_used = True
                print(f"[enhanced_ensemble] Ensemble created with {len(fitted)} models: {model_components}")
                
                # Predict per iteration with metrics tracking
                for it, group in df_norm.groupby('iteration', sort=True):
                    # Detection cost: time to compute selection (ICN method)
                    detection_start = time.perf_counter()
                    icn_selected = best_by_score[it]
                    detection_time = time.perf_counter() - detection_start
                    
                    # Prediction time: time for AI model to predict
                    Xg = group[feature_cols].fillna(0.0).values.astype(float)
                    pred_start = time.perf_counter()
                    
                    if model[2]:  # needs scaling
                        Xg_scaled = model[1].transform(Xg)
                        probs = model[0].predict_proba(Xg_scaled)[:,1]
                    else:
                        probs = model[0].predict_proba(Xg)[:,1]
                    
                    prediction_time = time.perf_counter() - pred_start
                    best_idx = int(np.argmax(probs))
                    predicted_router = group.iloc[best_idx]['Router']
                    predictions[it] = predicted_router
                    
                    # Get metrics for selected router
                    selected_row = group[group['Router'] == predicted_router].iloc[0]
                    chr_val = selected_row['CHR']
                    latency_val = selected_row['Latency_ms']
                    
                    # Hop reduction (pass df_norm and iteration for accurate calculation)
                    hop_reduction = calculate_hop_reduction(predicted_router, routers, df_norm, it)
                    
                    # Accuracy: does AI match ICN optimal?
                    accuracy = 1.0 if predicted_router == icn_selected else 0.0
                    
                    # Store metrics
                    metrics_tracking['iteration'].append(it)
                    metrics_tracking['CHR'].append(chr_val)
                    metrics_tracking['Latency'].append(latency_val)
                    metrics_tracking['HopReduction'].append(hop_reduction)
                    metrics_tracking['DetectionCost'].append(detection_time * 1000)  # Convert to ms
                    metrics_tracking['PredictionTime'].append(prediction_time * 1000)  # Convert to ms
                    metrics_tracking['Accuracy'].append(accuracy)
            else:
                model_used = False
                model = None
        except Exception as e:
            model_used = False
            model = None
            print(f"[enhanced_ensemble] training failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        model_used = False

    # Fallback to deterministic if model not used
    if not model_used:
        for it in best_by_score:
            predictions[it] = best_by_score[it]
            selected_row = df_norm[(df_norm['iteration'] == it) & (df_norm['Router'] == predictions[it])].iloc[0]
            metrics_tracking['iteration'].append(it)
            metrics_tracking['CHR'].append(selected_row['CHR'])
            metrics_tracking['Latency'].append(selected_row['Latency_ms'])
            metrics_tracking['HopReduction'].append(calculate_hop_reduction(predictions[it], routers, df_norm, it))
            metrics_tracking['DetectionCost'].append(0.0)  # ICN has minimal cost
            metrics_tracking['PredictionTime'].append(0.0)  # No ML prediction
            metrics_tracking['Accuracy'].append(1.0)  # Always matches itself

    # Save selection history
    select_out = selection_out if selection_out is not None else os.path.join(CSV_DIR, "network_selection_history.csv")
    selrows = []
    for it in sorted(predictions.keys()):
        selrows.append({
            "iteration": int(it),
            "best_by_model": predictions[it],
            "model_used": bool(model_used)
        })
    pd.DataFrame(selrows).to_csv(select_out, index=False)
    print(f"[enhanced_ensemble] Saved selection history to {select_out}")

    # Save metrics tracking
    metrics_df = pd.DataFrame(metrics_tracking)
    metrics_out = os.path.join(CSV_DIR, "performance_metrics.csv")
    metrics_df.to_csv(metrics_out, index=False)
    print(f"[enhanced_ensemble] Saved performance metrics to {metrics_out}")

    return {
        "metrics_df": df_norm,
        "selection_df": pd.DataFrame(selrows),
        "performance_metrics_df": metrics_df,
        "model_used": bool(model_used),
        "model": model,
        "model_components": model_components
    }

