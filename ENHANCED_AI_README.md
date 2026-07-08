# Enhanced AI Network Recommender with ML/DL Ensemble

## Overview

This enhanced AI-based router recommendation system uses an advanced Machine Learning and Deep Learning ensemble to select the best cache router (CR) for network optimization. The system tracks comprehensive performance metrics and generates detailed visualizations.

## Features

### 1. Advanced ML/DL Ensemble
- **Random Forest Classifier** (200 estimators)
- **Extra Trees Classifier** (200 estimators)
- **Gradient Boosting Classifier** (200 estimators)
- **Neural Network (MLP)** (100-50 hidden layers)
- **XGBoost** (optional, if installed)
- **LightGBM** (optional, if installed)

The ensemble uses soft voting to combine predictions from multiple models, improving accuracy and robustness.

### 2. Comprehensive Performance Metrics

The system tracks 6 key metrics:

1. **CHR (Cache Hit Ratio)**: Percentage of cache hits vs total requests
2. **Latency**: Average latency in milliseconds
3. **Hop Reduction**: Reduction in network hops achieved by selecting optimal cache router
4. **Detection Cost**: Computation time (ms) to select a cache router using ICN method
5. **Prediction Time**: Time (ms) for AI model to predict the best router
6. **Accuracy**: How often AI selection matches the optimal ICN selection

### 3. Visualization

The system generates multiple plot types:

- **Individual Metric Plots**: Line charts for each metric over iterations
- **Combined Normalized Plot**: All metrics on one chart (normalized 0-1)
- **Subplot Grid**: 2x3 grid showing all metrics simultaneously
- **Statistical Summary**: Box plots and distribution statistics for each metric
- **AI vs ICN Comparison**: Side-by-side comparison of AI and ICN performance

## Files

### Core Files
- `ai_network_recommender_enhanced.py`: Enhanced ensemble training and prediction
- `plot_performance_metrics.py`: Comprehensive plotting functions
- `test_enhanced_ai.py`: Main test script that runs the full pipeline
- `comparison_ai_icn.py`: AI vs ICN comparison (existing)

### Output Files
- `Path_Iterations/network_metrics.csv`: Raw router metrics per iteration
- `Path_Iterations/network_selection_history.csv`: AI and ICN selections per iteration
- `Path_Iterations/performance_metrics.csv`: Comprehensive performance metrics
- `Path_Iterations/plots/*.png`: All generated visualizations

## Usage

### Basic Usage

```python
from ai_network_recommender_enhanced import collect_network_metrics, enhanced_ensemble_train_and_predict
from plot_performance_metrics import plot_all_performance_metrics

# 1. Collect metrics
metrics_csv = collect_network_metrics(routers, n_iterations=50)

# 2. Train ensemble and generate predictions
result = enhanced_ensemble_train_and_predict(
    metrics_csv=metrics_csv,
    min_iters_for_training=8,
    routers=routers
)

# 3. Generate plots
plot_paths = plot_all_performance_metrics(
    metrics_csv="Path_Iterations/performance_metrics.csv"
)
```

### Running the Full Pipeline

```bash
python test_enhanced_ai.py
```

This will:
1. Load or create network topology
2. Collect network metrics
3. Train enhanced ML/DL ensemble
4. Generate all performance plots
5. Compare AI vs ICN performance

## Installation

### Required Packages
```bash
pip install pandas numpy matplotlib scikit-learn
```

### Optional Packages (for enhanced ensemble)
```bash
pip install xgboost lightgbm
```

Note: The system works without XGBoost and LightGBM, using only sklearn models.

## Performance Metrics Explained

### CHR (Cache Hit Ratio)
- **Higher is better**
- Measures effectiveness of cache placement
- Range: 0.0 to 1.0

### Latency
- **Lower is better**
- Average response time in milliseconds
- Critical for user experience

### Hop Reduction
- **Higher is better**
- Measures reduction in network hops by selecting optimal cache router
- Range: 0.0 to 1.0
- Calculated based on router centrality (CMBA)

### Detection Cost
- **Lower is better**
- Time taken for ICN method to compute optimal router
- Measured in milliseconds
- Represents computational overhead

### Prediction Time
- **Lower is better**
- Time taken for AI ensemble to predict best router
- Measured in milliseconds
- Includes model inference time

### Accuracy
- **Higher is better**
- Percentage of iterations where AI selection matches ICN optimal selection
- Range: 0.0 to 1.0
- Indicates how well AI learns optimal patterns

## Model Selection

The ensemble automatically:
1. Evaluates all available models using cross-validation
2. Selects models with accuracy >= 90% of mean score
3. Creates a voting classifier with selected models
4. Uses soft voting (probability averaging) for predictions

## Results Interpretation

### Good Performance Indicators
- **High CHR**: Effective cache placement
- **Low Latency**: Fast response times
- **High Hop Reduction**: Efficient network routing
- **Low Prediction Time**: Fast AI inference
- **High Accuracy**: AI matches optimal selections

### Example Results
```
CHR: 0.846 (84.6% cache hit rate)
Latency: 45.99ms (good response time)
Hop Reduction: Variable (depends on router positions)
Detection Cost: <1ms (very fast ICN computation)
Prediction Time: ~99ms (acceptable for ML inference)
Accuracy: 82% (AI matches optimal 82% of the time)
```

## Customization

### Adjusting Ensemble Weights
Edit `ai_network_recommender_enhanced.py`:
```python
df_norm['ai_performance_score'] = (
    df_norm['n_CHR'] * 0.30 +      # Adjust CHR weight
    df_norm['n_CMBA'] * 0.20 +     # Adjust CMBA weight
    df_norm['n_Latency'] * 0.30 +  # Adjust Latency weight
    df_norm['n_CacheOcc'] * 0.20   # Adjust Cache Occupancy weight
)
```

### Adding New Metrics
1. Add metric calculation in `enhanced_ensemble_train_and_predict()`
2. Add to `metrics_tracking` dictionary
3. Update `plot_performance_metrics.py` to include new metric

## Troubleshooting

### Issue: "XGBoost/LightGBM not available"
- **Solution**: Install optional packages or use without them (system works with sklearn only)

### Issue: "Not enough iterations for training"
- **Solution**: Increase `n_iterations` or decrease `min_iters_for_training`

### Issue: "All models have low accuracy"
- **Solution**: Check data quality, ensure sufficient iterations, verify feature columns

## Performance Tips

1. **More Iterations**: Better training data = better model performance
2. **Feature Engineering**: Add more router metrics if available
3. **Model Tuning**: Adjust hyperparameters in model definitions
4. **Ensemble Size**: More models = better accuracy but slower prediction

## Future Enhancements

- Real-time hop reduction calculation from actual network paths
- Deep learning models (LSTM, Transformer) for sequence prediction
- Online learning for adaptive model updates
- Multi-objective optimization (Pareto frontier)
- Explainable AI (SHAP values, feature importance)

## Contact

For issues or questions, refer to the main project documentation.

