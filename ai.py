# ai.py
"""
AI + Manual process modes for selecting cache router per selected path.

How to use (example at bottom):
- Prepare a list of router rows for the selected path, each dict:
  {'Router':'R1','Cache occupy':5,'CMBA':2,'Latency(s)':1.2,'CHR':9}
- Call manual_iteration(path_rows, iteration_id, path_name) to compute, save, and pick.
- Call ai_iteration(path_rows, iteration_id, path_name) to compute, save, and get ensemble recommendation.
- Call plot_path_iterations(path_name) to plot horizontal-bar performance graph for all saved iterations for that path.

Files created:
- Path_Iterations/{path_name}.csv  (per-iteration rows appended)
- Path_Iterations/{path_name}_selection_history.csv
- Path_Iterations/{path_name}_ensemble_train.csv  (internal training snapshot)
- Path_Iterations/plots/... PNGs
"""

import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.exceptions import NotFittedError
import matplotlib.pyplot as plt

CSV_DIR = "Path_Iterations"
os.makedirs(CSV_DIR, exist_ok=True)
PLOT_DIR = os.path.join(CSV_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# --- Utilities: normalization & scoring ---
def normalize_vector(vals: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(vals, errors='coerce').astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or abs(mx - mn) < 1e-12:
        return pd.Series([1.0] * len(s), index=s.index)
    if higher_is_better:
        return (s - mn) / (mx - mn)
    else:
        return (mx - s) / (mx - mn)

def compute_iteration_df(router_rows: List[Dict[str, Any]], iteration_id: int, path_name: str) -> pd.DataFrame:
    """
    Compute normalized metrics and average score for routers in selected path for one iteration.
    Returns DataFrame ready to append to CSV.
    """
    df = pd.DataFrame(router_rows).copy()
    # ensure numeric
    for col in ['Cache occupy', 'CMBA', 'Latency(s)', 'CHR']:
        if col not in df.columns:
            raise KeyError(f"Missing column {col} in router_rows")
        df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)

    # Normalize: CMBA & CHR -> higher is better; Cache occupy & Latency -> lower is better
    df['norm_CMBA'] = normalize_vector(df['CMBA'], higher_is_better=True)
    df['norm_CHR']  = normalize_vector(df['CHR'], higher_is_better=True)
    df['norm_CacheOccupy'] = normalize_vector(df['Cache occupy'], higher_is_better=False)
    df['norm_Latency'] = normalize_vector(df['Latency(s)'], higher_is_better=False)

    df['avg_score'] = df[['norm_CMBA','norm_CHR','norm_CacheOccupy','norm_Latency']].mean(axis=1)

    # meta
    df['iteration'] = iteration_id
    df['path_name'] = path_name

    # reorder and return
    cols = ['iteration','path_name','Router','Cache occupy','CMBA','Latency(s)','CHR',
            'norm_CMBA','norm_CHR','norm_CacheOccupy','norm_Latency','avg_score']
    return df[cols]

def path_csv_path(path_name: str) -> str:
    safe = path_name.replace(" ", "_")
    return os.path.join(CSV_DIR, f"{safe}.csv")

def append_iteration(df_iteration: pd.DataFrame, path_name: str):
    fn = path_csv_path(path_name)
    header = not os.path.exists(fn)
    df_iteration.to_csv(fn, mode='a', index=False, header=header)

# --- Manual process mode ---
def manual_iteration(router_rows: List[Dict[str, Any]], iteration_id: int, path_name: str) -> Tuple[str, pd.Series]:
    """
    Runs the manual process mode for one iteration:
      - computes normalized scores,
      - appends to Path_Iterations/{path_name}.csv,
      - selects router with highest avg_score (ties -> higher CHR, lower Latency).
    Returns (chosen_router, chosen_row_series).
    """
    df_iter = compute_iteration_df(router_rows, iteration_id, path_name)
    append_iteration(df_iter, path_name)

    # selection: highest avg_score, tie-breaker CHR desc, Latency asc
    chosen = df_iter.sort_values(by=['avg_score','CHR','Latency(s)'], ascending=[False,False,True]).iloc[0]
    # append to selection history
    selection_fn = os.path.join(CSV_DIR, f"{path_name.replace(' ','_')}_selection_history.csv")
    rec = {
        'iteration': iteration_id,
        'path_name': path_name,
        'chosen_router': chosen['Router'],
        'chosen_avg_score': float(chosen['avg_score']),
        'chosen_CHR': float(chosen['CHR']),
        'chosen_Latency': float(chosen['Latency(s)'])
    }
    sel_df = pd.DataFrame([rec])
    sel_df.to_csv(selection_fn, mode='a', index=False, header=not os.path.exists(selection_fn))
    return chosen['Router'], chosen

# --- AI Recommended process mode (Ensemble with pruning) ---
def _prepare_training_data(path_name: str) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Read existing path CSV and produce features X and target y:
    - features: avg_score components or raw metrics per-row aggregated by iteration
    - target: router chosen by manual selection (highest avg_score) per iteration
    If selection_history exists, use it to label each iteration.
    """
    fn = path_csv_path(path_name)
    if not os.path.exists(fn):
        return pd.DataFrame(), pd.Series(dtype=object)
    df = pd.read_csv(fn)
    # Need selection_history to know which router was chosen historically
    sel_fn = os.path.join(CSV_DIR, f"{path_name.replace(' ','_')}_selection_history.csv")
    if not os.path.exists(sel_fn):
        return pd.DataFrame(), pd.Series(dtype=object)
    sel = pd.read_csv(sel_fn)
    # build per-iteration features: for each iteration create row per router (we'll flatten)
    # We'll use features: Cache occupy, CMBA, Latency(s), CHR, avg_score and Router label
    df_features = df[['iteration','Router','Cache occupy','CMBA','Latency(s)','CHR','avg_score']].copy()
    # Merge with selection to get 'chosen' flag per iteration
    merged = df_features.merge(sel[['iteration','chosen_router']], on='iteration', how='left')
    merged['label_is_chosen'] = (merged['Router'] == merged['chosen_router']).astype(int)
    # For classifier training we want to predict which Router in that iteration will be chosen.
    # Transform per-iteration data to features: we will one-hot/encode Router and include metrics.
    # Simpler approach: keep per-router rows and predict label_is_chosen.
    X = merged[['Router','Cache occupy','CMBA','Latency(s)','CHR','avg_score']].copy()
    y = merged['label_is_chosen']
    return X, y

def _encode_features(X: pd.DataFrame) -> Tuple[np.ndarray, LabelEncoder]:
    """
    Encode Router categorical feature and return numpy array features; return encoder to decode later.
    """
    Xc = X.copy()
    le = LabelEncoder()
    Xc['Router_enc'] = le.fit_transform(Xc['Router'])
    Xc = Xc[['Router_enc','Cache occupy','CMBA','Latency(s)','CHR','avg_score']]
    return Xc.values.astype(float), le

def _train_and_prune_ensemble(X: np.ndarray, y: np.ndarray, min_models=2, cv=3) -> VotingClassifier:
    """
    Train an ensemble of three diverse tree-based classifiers and prune out weak performers.
    Returns a fitted VotingClassifier made of the retained classifiers.
    If not enough data or all models are weak, returns None.
    """
    # raw models
    models = [
        ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
        ('et', ExtraTreesClassifier(n_estimators=100, random_state=42)),
        ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42))
    ]
    # Evaluate each with cross_val_score and keep those above threshold
    scores = {}
    for name, m in models:
        try:
            sc = cross_val_score(m, X, y, cv=min(cv, max(2, min(5, len(y)))))  # adapt cv
            scores[name] = float(np.mean(sc))
        except Exception:
            scores[name] = 0.0
    # dynamic threshold: keep models with score >= mean(scores) or at least 0.5 if mean is low
    mean_score = np.mean(list(scores.values())) if scores else 0.0
    threshold = max(0.5, mean_score)
    kept = [m for (n,m) in models if scores.get(n,0.0) >= threshold]
    if len(kept) < min_models:
        # relax threshold: keep top min_models models
        sorted_models = sorted(models, key=lambda nm: scores.get(nm[0],0.0), reverse=True)
        kept = [m for (_,m) in sorted_models[:min_models]]
    # fit kept models
    fitted = []
    for m in kept:
        m.fit(X, y)
        fitted.append((type(m).__name__, m))
    # combine into voting
    if not fitted:
        return None
    vc = VotingClassifier(estimators=fitted, voting='soft')
    vc.fit(X, y)  # final fit
    return vc

def ai_iteration(router_rows: List[Dict[str, Any]], iteration_id: int, path_name: str) -> Tuple[str, dict]:
    """
    Runs AI recommended iteration:
     - computes normalized scores and saves iteration to CSV,
     - tries to train/prune ensemble on historical data and predict the chosen router for this iteration,
     - if training data insufficient, falls back to deterministic highest avg_score (same as manual).
    Returns (recommended_router, info_dict)
    """
    # compute & save iteration as usual
    df_iter = compute_iteration_df(router_rows, iteration_id, path_name)
    append_iteration(df_iter, path_name)

    # Try to prepare training data
    X_df, y_series = _prepare_training_data(path_name)
    info = {'used_ensemble': False, 'fallback': False, 'model_scores': None, 'ensemble_voted': None}
    recommended = None

    if not X_df.empty and len(y_series.dropna()) >= 10:
        # enough history: encode and train/prune
        X_np, le = _encode_features(X_df)
        y = y_series.values.astype(int)
        try:
            ensemble = _train_and_prune_ensemble(X_np, y, min_models=2, cv=3)
            info['used_ensemble'] = ensemble is not None
            if ensemble is not None:
                # Build features of current iteration (rows in df_iter) for prediction
                curr = df_iter[['Router','Cache occupy','CMBA','Latency(s)','CHR','avg_score']].copy()
                # encode Router using encoder fit earlier - ensure unseen routers handled
                # If unseen router present, append to label encoder mapping by using transform on known plus mapping new to new ints
                # Simpler: map Router names to encoder classes where possible; unseen -> assign -1 and pad features
                router_names = X_df['Router'].unique().tolist()
                # create temp label encoder fit on historical routers (we have 'le')
                try:
                    # In our encode pipeline we returned a LabelEncoder fitted on X_df
                    encoder = le
                    # we need to transform current routers; if unseen, add a new label index
                    curr_enc = []
                    for r in curr['Router']:
                        if r in encoder.classes_:
                            curr_enc.append(int(np.where(encoder.classes_ == r)[0][0]))
                        else:
                            # append as new index (position at end)
                            curr_enc.append(len(encoder.classes_))
                    curr['Router_enc'] = curr_enc
                    feat_cols = ['Router_enc','Cache occupy','CMBA','Latency(s)','CHR','avg_score']
                    X_curr = curr[feat_cols].values.astype(float)
                except Exception:
                    # fallback - use average based selection
                    X_curr = curr[['Cache occupy','CMBA','Latency(s)','CHR','avg_score']].values.astype(float)
                # predict probabilities: since ensemble was trained to predict chosen router per router-row (label 1 means chosen)
                try:
                    probs = ensemble.predict_proba(X_curr)[:,1]  # probability that row is the chosen router
                    curr['chosen_prob'] = probs
                    # choose router with highest chosen_prob; tie-break by avg_score
                    chosen_row = curr.sort_values(by=['chosen_prob','avg_score'], ascending=[False,False]).iloc[0]
                    recommended = chosen_row['Router']
                    info['ensemble_voted'] = recommended
                except Exception as e:
                    info['error_predict'] = str(e)
                    recommended = None
        except Exception as e:
            info['train_error'] = str(e)
            recommended = None

    # if not recommended by ensemble, fallback to rule (highest avg_score)
    if not recommended:
        info['fallback'] = True
        chosen = df_iter.sort_values(by=['avg_score','CHR','Latency(s)'], ascending=[False,False,True]).iloc[0]
        recommended = chosen['Router']

    # append to selection history with 'ai_recommend' field
    selection_fn = os.path.join(CSV_DIR, f"{path_name.replace(' ','_')}_selection_history.csv")
    rec = {
        'iteration': iteration_id,
        'path_name': path_name,
        'ai_recommend_router': recommended,
        'ai_used_ensemble': info.get('used_ensemble', False),
        'ai_fallback_used': info.get('fallback', False)
    }
    sel_df = pd.DataFrame([rec])
    sel_df.to_csv(selection_fn, mode='a', index=False, header=not os.path.exists(selection_fn))

    # Save separate training snapshot for debugging if ensemble used
    if info.get('used_ensemble'):
        try:
            train_snap = X_df.copy()
            train_snap['label'] = y_series.values
            train_snap_fn = os.path.join(CSV_DIR, f"{path_name.replace(' ','_')}_ensemble_train.csv")
            train_snap.to_csv(train_snap_fn, index=False)
        except Exception:
            pass

    return recommended, info

# --- Plotting: requested graph (Y-axis routers with iterations, X-axis net performance) ---
def plot_path_iterations(path_name: str, save_png: bool = True) -> pd.DataFrame:
    """
    Read Path_Iterations/{path_name}.csv and produce plot:
     - Y-axis: rows for each router+iteration (e.g. "iter1_R1")
     - X-axis: avg_score (net performance)
    Saves PNG to Path_Iterations/plots/{path_name}_performance.png
    Returns DataFrame used for plotting.
    """
    fn = path_csv_path(path_name)
    if not os.path.exists(fn):
        raise FileNotFoundError(f"No iterations file found for path {path_name}. Expected {fn}")
    df = pd.read_csv(fn)
    # create label per-row
    df['row_label'] = df.apply(lambda r: f"iter{int(r['iteration'])}_{r['Router']}", axis=1)
    # sort by iteration asc, then by avg_score desc
    df = df.sort_values(by=['iteration','avg_score'], ascending=[True, False]).reset_index(drop=True)
    labels = df['row_label'].tolist()
    scores = df['avg_score'].tolist()

    # horizontal bar plot
    plt.figure(figsize=(9, max(4, 0.3 * len(labels))))
    y_pos = np.arange(len(labels))
    plt.barh(y_pos, scores, align='center')
    plt.yticks(y_pos, labels)
    plt.xlabel('Net Performance (avg_score)')
    plt.title(f'Per-iteration router net performance: {path_name}')
    plt.gca().invert_yaxis()  # highest iteration on top
    plt.tight_layout()
    png_path = os.path.join(PLOT_DIR, f"{path_name.replace(' ','_')}_performance.png")
    if save_png:
        plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.close()
    return df

# --- Convenience function: run both modes for same input and produce summary plot ---
def run_manual_and_ai(router_rows: List[Dict[str,Any]], iteration_id: int, path_name: str):
    manual_choice, _ = manual_iteration(router_rows, iteration_id, path_name)
    ai_choice, info = ai_iteration(router_rows, iteration_id, path_name)
    plot_df = plot_path_iterations(path_name)
    summary = {
        'path': path_name,
        'iteration': iteration_id,
        'manual_choice': manual_choice,
        'ai_choice': ai_choice,
        'ai_info': info,
        'plot_rows': len(plot_df)
    }
    return summary

# ---------------- Example usage ----------------
if __name__ == "__main__":
    # Example top-table routers (use your real values or call from main.py)
    router_table = [
        {'Router':'R1', 'Cache occupy':5,  'CMBA':2, 'Latency(s)':1.2, 'CHR':9},
        {'Router':'R2', 'Cache occupy':10, 'CMBA':4, 'Latency(s)':2.0, 'CHR':10},
        {'Router':'R3', 'Cache occupy':15, 'CMBA':9, 'Latency(s)':3.0, 'CHR':2},
        {'Router':'R4', 'Cache occupy':20, 'CMBA':7, 'Latency(s)':5.0, 'CHR':8},
    ]
    selected_path = ['R1','R4']  # example path
    path_rows = [r for lab in selected_path for r in router_table if r['Router']==lab]

    print("Running manual + AI iteration example for path 'user_R1_R4' iteration 1")
    summary = run_manual_and_ai(path_rows, iteration_id=1, path_name='user_R1_R4')
    print(summary)
    print("Files written to Path_Iterations/ (CSV + plots).")
