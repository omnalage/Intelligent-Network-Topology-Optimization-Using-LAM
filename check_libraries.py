# Quick check for required libraries
try:
    import xgboost
    print("XGBoost: Available")
except:
    print("XGBoost: Not installed (optional)")

try:
    import lightgbm
    print("LightGBM: Available")
except:
    print("LightGBM: Not installed (optional)")

try:
    from sklearn.neural_network import MLPClassifier
    print("Neural Network (sklearn): Available")
except:
    print("Neural Network: Not available")

print("\nNote: XGBoost and LightGBM are optional. The system will work with base sklearn models.")

