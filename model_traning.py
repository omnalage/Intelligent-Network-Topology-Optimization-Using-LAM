import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import pickle

# Use the combined processed file produced by Dataset Preprocessing.py
DATAFILE = "Processed_Features_with_Policy.csv"

FEATURES = ['No of Clients', 'Total Requests', 'Hop Reduction', 'Cache Hit Ratio', 'Latency']
TARGET   = 'Policy'  # <-- train to predict the policy

def main():
    if not os.path.exists(DATAFILE):
        raise FileNotFoundError(f"'{DATAFILE}' not found. Run 'Dataset Preprocessing.py' first.")

    df = pd.read_csv(DATAFILE)

    X = df[FEATURES].copy()
    y = df[TARGET].astype(str)  # scikit-learn can handle string labels

    # simple scaling (optional but consistent with preprocessing)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print(f"Accuracy: {accuracy_score(y_test, y_pred)*100:.2f}%")
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    # Save ONLY the model (no encoders needed because y is strings)
    os.makedirs("models", exist_ok=True)
    with open("models/random_forest_model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("Saved model to models/random_forest_model.pkl")

if __name__ == "__main__":
    main()
