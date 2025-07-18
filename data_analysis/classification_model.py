import os
import pandas as pd
from transformers import AutoModel, AutoTokenizer
import torch
import numpy as np
from sklearn.model_selection import KFold, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder

# --- Path Configuration ---
# Get the directory of the current notebook (assuming this script is run directly)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Parent directory is the project root
PROJECT_ROOT = os.path.dirname(current_dir)
print(f"Project root identified as: {PROJECT_ROOT}")

# Set paths - CONFIGURABLE PARAMETERS
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATA_FILENAME = "data.csv"

# Output directory for embeddings
EMBEDDINGS_DIR = os.path.join(PROJECT_ROOT, "embeddings")
os.makedirs(EMBEDDINGS_DIR, exist_ok=True) # Ensure embeddings directory exists
EMBEDDINGS_FILENAME = "distilbert_embeddings_and_labels.npz" # .npz for multiple arrays

# Construct full path to the data file
DATA_PATH = os.path.join(DATA_DIR, DATA_FILENAME)
print(f"Looking for data at: {DATA_PATH}")

# Load the data
try:
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded dataset with shape: {df.shape}")
except FileNotFoundError:
    print(f"Error: Data file not found at {DATA_PATH}. Please ensure the file exists.")
    exit()

# Ensure the text fields are strings
df['english_text'] = df['english_text'].astype(str)
df['chinese_text'] = df['chinese_text'].astype(str)
df['other_information'] = df['other_information'].astype(str)
df['success'] = df['success'].astype(str)
df['technique'] = df['technique'].astype(str)
df['intent'] = df['intent'].astype(str)

# Display basic information
print("\nDataFrame Info:")
df.info()
print("\nDataFrame Head (first 10 rows):")
print(df.head(10))

# --- Model Loading (DistilBERT - chosen for robustness) ---
# model_name = "microsoft/deberta-v3-base" # This caused tiktoken issues
model_name = "distilbert-base-uncased" # Smaller model for faster inference and fewer dependency issues

print(f"\nLoading tokenizer and model: {model_name}...")
# For DistilBERT, use_fast=True (default) is typically preferred and faster.
# Removed `use_fast=False` as it's not needed for DistilBERT and might hinder performance slightly.
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval() # Set model to evaluation mode
print(f"Using model: {model_name} on device: {device}")

# --- Embedding Function ---
def get_prompt_embedding(text):
    """
    Generates an embedding for a given text using the pre-trained model.
    Uses the [CLS] token embedding as the sequence representation.
    """
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad(): # Disable gradient calculation for inference
        outputs = model(**inputs)

    # Use the embedding of the [CLS] token (first token)
    embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
    return embedding.flatten() # Flatten to a 1D vector

# --- Preprocessing Data from DataFrame ---
print("\nPreprocessing data from DataFrame...")

# Handle 'nan' values in 'success' column BEFORE encoding
# Replace string 'nan' with actual numpy.nan, then drop rows where 'success' is NaN
df['success'] = df['success'].replace('nan', np.nan)
df_cleaned = df.dropna(subset=['success']).copy() # Use .copy() to avoid SettingWithCopyWarning

print(f"DataFrame after handling 'nan' in 'success': {df_cleaned.shape}")

# Extract prompts (english_text column) from the CLEANED DataFrame
your_prompts = df_cleaned['english_text'].tolist()

# Extract labels (success column) from the CLEANED DataFrame
label_encoder = LabelEncoder()
# Ensure values are treated as strings before encoding, even after dropna
your_labels = label_encoder.fit_transform(df_cleaned['success'].astype(str))

# Verify the mapping (FIXED: used label_encoder.classes_ instead of label_labels.classes_)
print(f"Original 'success' values present in cleaned data: {df_cleaned['success'].unique()}")
print(f"Encoded 'success' labels mapping: {label_encoder.classes_} -> {np.arange(len(label_encoder.classes_))}")
print(f"First 5 prompts: {your_prompts[:5]}")
print(f"First 5 labels (encoded): {your_labels[:5]}")
print(f"Total prompts for training: {len(your_prompts)}, Total labels for training: {len(your_labels)}")

# --- Generate Prompt Embeddings ---
print(f"\nGenerating embeddings for {len(your_prompts)} prompts...")
prompt_embeddings = []
for i, prompt in enumerate(your_prompts):
    try:
        embedding = get_prompt_embedding(prompt)
        prompt_embeddings.append(embedding)
    except Exception as e:
        print(f"Error generating embedding for prompt {i}: '{prompt[:50]}...' Error: {e}")
        # Append a zero vector if an error occurs to maintain consistent array shape
        prompt_embeddings.append(np.zeros(model.config.hidden_size))

X = np.array(prompt_embeddings)
y = np.array(your_labels)

print(f"Generated X (embeddings) with shape: {X.shape}")
print(f"Generated y (labels) with shape: {y.shape}")

# --- Save Embeddings and Labels ---
embeddings_output_path = os.path.join(EMBEDDINGS_DIR, EMBEDDINGS_FILENAME)
np.savez_compressed(embeddings_output_path, X=X, y=y)
print(f"\nEmbeddings and labels saved to: {embeddings_output_path}")

# To load them later:
# loaded_data = np.load(embeddings_output_path)
# X_loaded = loaded_data['X']
# y_loaded = loaded_data['y']


# --- Model Training with K-Fold Cross-Validation ---
print("\nStarting K-Fold Cross-Validation...")

# Recommend using KFold Cross-Validation because your dataset is small
kf = KFold(n_splits=10, shuffle=True, random_state=42) # 5-fold CV, shuffles data

# --- Logistic Regression ---
print("\n--- Logistic Regression Model ---")
# 'balanced' class_weight automatically adjusts weights inversely proportional to class frequencies
log_reg_model = LogisticRegression(solver='liblinear', random_state=42, class_weight='balanced', max_iter=1000)
scores_log_reg = cross_val_score(log_reg_model, X, y, cv=kf, scoring='f1_macro') # F1-macro for imbalanced classification
print(f"Logistic Regression F1-macro scores per fold: {scores_log_reg}")
print(f"Logistic Regression Mean F1-macro: {scores_log_reg.mean():.4f} (+/- {scores_log_reg.std() * 2:.4f})")


# --- Support Vector Machine (SVM) ---
print("\n--- Support Vector Machine (SVM) Model ---")
svm_model = SVC(kernel='linear', random_state=42, class_weight='balanced')
scores_svm = cross_val_score(svm_model, X, y, cv=kf, scoring='f1_macro')
print(f"SVM F1-macro scores per fold: {scores_svm}")
print(f"SVM Mean F1-macro: {scores_svm.mean():.4f} (+/- {scores_svm.std() * 2:.4f})")

print("\n--- Support Vector Machine (SVM) with RBF Kernel ---")
# Use RBF kernel. class_weight='balanced' is still important for imbalance.
# Start with default C and gamma, then tune.
svm_rbf_model = SVC(kernel='rbf', random_state=42, class_weight='balanced')
scores_svm_rbf = cross_val_score(svm_rbf_model, X, y, cv=kf, scoring='f1_macro')
print(f"SVM (RBF) F1-macro scores per fold: {scores_svm_rbf}")
print(f"SVM (RBF) Mean F1-macro: {scores_svm_rbf.mean():.4f} (+/- {scores_svm_rbf.std() * 2:.4f})")

from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

print("\n--- Random Forest Classifier ---")
# class_weight='balanced' is also available here
rf_model = RandomForestClassifier(random_state=42, class_weight='balanced', n_estimators=100, max_depth=10)
scores_rf = cross_val_score(rf_model, X, y, cv=kf, scoring='f1_macro')
print(f"Random Forest F1-macro scores per fold: {scores_rf}")
print(f"Random Forest Mean F1-macro: {scores_rf.mean():.4f} (+/- {scores_rf.std() * 2:.4f})")

print("\n--- XGBoost Classifier ---")
# Use a smaller learning_rate and more estimators with a limited max_depth for small datasets
xgb_model = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss',
                          n_estimators=100, learning_rate=0.1, max_depth=5,
                          scale_pos_weight=np.sum(y == 0) / np.sum(y == 1)) # Handles imbalance
scores_xgb = cross_val_score(xgb_model, X, y, cv=kf, scoring='f1_macro')
print(f"XGBoost F1-macro scores per fold: {scores_xgb}")
print(f"XGBoost Mean F1-macro: {scores_xgb.mean():.4f} (+/- {scores_xgb.std() * 2:.4f})")

print("\n--- LightGBM Classifier ---")
# Similar to XGBoost, generally faster
lgbm_model = LGBMClassifier(random_state=42, n_estimators=100, learning_rate=0.1, max_depth=5,
                           is_unbalance=True) # or scale_pos_weight for imbalance
scores_lgbm = cross_val_score(lgbm_model, X, y, cv=kf, scoring='f1_macro')
print(f"LightGBM F1-macro scores per fold: {scores_lgbm}")
print(f"LightGBM Mean F1-macro: {scores_lgbm.mean():.4f} (+/- {scores_lgbm.std() * 2:.4f})")

print(f"\nOverall Mean F1-macro Scores:")
print(f"Logistic Regression: {scores_log_reg.mean():.4f} (+/- {scores_log_reg.std() * 2:.4f})")
print(f"SVM (Linear): {scores_svm.mean():.4f} (+/- {scores_svm.std() * 2:.4f})")
print(f"SVM (RBF): {scores_svm_rbf.mean():.4f} (+/- {scores_svm_rbf.std() * 2:.4f})")
print(f"Random Forest: {scores_rf.mean():.4f} (+/- {scores_rf.std() * 2:.4f})")
print(f"XGBoost: {scores_xgb.mean():.4f} (+/- {scores_xgb.std() * 2:.4f})")
print(f"LightGBM: {scores_lgbm.mean():.4f} (+/- {scores_lgbm.std() * 2:.4f})")

print("\nCross-validation complete.")

import matplotlib.pyplot as plt
import seaborn as sns
# --- Calculate Standard Deviations (already present in your code) ---
stds_log_reg = scores_log_reg.std()
stds_svm = scores_svm.std()
stds_svm_rbf = scores_svm_rbf.std()
stds_rf = scores_rf.std()
stds_xgb = scores_xgb.std()
stds_lgbm = scores_lgbm.std()

# Create a list of standard deviations in the same order as your means
variances_to_plot = [
    stds_log_reg,
    stds_svm,
    stds_svm_rbf,
    stds_rf,
    stds_xgb,
    stds_lgbm
]
'''
# --- Prepare data for plotting (Explicitly convert to NumPy arrays) ---
model_labels = np.array(['Logistic Regression', 'SVM (Linear)', 'SVM (RBF)',
                         'Random Forest', 'XGBoost', 'LightGBM'])
mean_scores = np.array([scores_log_reg.mean(), scores_svm.mean(),
                        scores_svm_rbf.mean(), scores_rf.mean(), scores_xgb.mean(), scores_lgbm.mean()])
std_errors = np.array(variances_to_plot)
print(f"\nModel Labels shape: {model_labels.shape}")
print(f"Mean scores shape: {mean_scores.shape}")
print(f"Standard deviations shape: {std_errors.shape}") 

# --- Visualize Results ---
plt.figure(figsize=(10, 6))

# Pass NumPy arrays to seaborn.barplot
sns.barplot(
    x=model_labels,
    y=mean_scores,
    yerr=std_errors, # This is the key addition to show variance
    palette='viridis' # Optional: Adds a nice color palette
)

plt.title(f'Mean F1-macro Scores and Variance for Different Models ({10}-Fold CV)')
plt.ylabel('Mean F1-macro Score')
plt.ylim(0, 1)
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

# Ensure the results directory exists
results_dir = os.path.join(PROJECT_ROOT, "results")
os.makedirs(results_dir, exist_ok=True)

plt.savefig(os.path.join(results_dir, "model_comparison_with_variance.png"))
plt.show()
'''

model_labels = ['Logistic Regression', 'SVM (Linear)', 'SVM (RBF)',
                'Random Forest', 'XGBoost', 'LightGBM']
mean_scores = [scores_log_reg.mean(), scores_svm.mean(),
               scores_svm_rbf.mean(), scores_rf.mean(), scores_xgb.mean(), scores_lgbm.mean()]
std_errors = [stds_log_reg, stds_svm, stds_svm_rbf, stds_rf, stds_xgb, stds_lgbm]

# Convert lists to NumPy arrays (good practice for plotting)
mean_scores_np = np.array(mean_scores)
std_errors_np = np.array(std_errors)

# --- Visualize Results using Matplotlib's plt.bar ---
plt.figure(figsize=(10, 6))

# plt.bar directly
# x: positions for the bars (integers 0, 1, 2, ...)
# height: the mean scores
# yerr: the standard deviations for error bars
# tick_label: labels for the x-axis ticks
plt.bar(
    x=np.arange(len(model_labels)), # Positions for bars (0, 1, 2, ...)
    height=mean_scores_np,
    yerr=std_errors_np, # Pass the NumPy array of standard deviations
    capsize=5, # Size of the error bar caps
    color=sns.color_palette('viridis', len(model_labels)) # Use seaborn palette for colors
)

plt.title(f'Mean F1-macro Scores and Variance for Different Models ({10}-Fold CV)')
plt.xlabel('Model')
plt.ylabel('Mean F1-macro Score')
plt.ylim(0, 1) # F1-macro score ranges from 0 to 1

# Set x-axis tick labels
plt.xticks(
    ticks=np.arange(len(model_labels)), # Positions of the ticks
    labels=model_labels,                 # Corresponding labels
    rotation=45,                         # Rotate labels
    ha='right'                           # Horizontal alignment
)

plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout() # Adjust layout to prevent labels from overlapping

# Ensure the results directory exists
results_dir = os.path.join(PROJECT_ROOT, "results")
os.makedirs(results_dir, exist_ok=True)

plt.savefig(os.path.join(results_dir, "model_comparison_with_variance.png"))
plt.show()