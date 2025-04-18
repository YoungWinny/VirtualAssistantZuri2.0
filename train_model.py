import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, confusion_matrix
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk
import pickle

# Download NLTK resources
nltk.download('punkt')
nltk.download('wordnet')

# Preprocessing: Lemmatization
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    words = word_tokenize(text.lower())  # Tokenize and convert to lower case
    lemmatized_words = [lemmatizer.lemmatize(word) for word in words if word.isalpha()]  # Lemmatize and remove non-alphabetical tokens
    return ' '.join(lemmatized_words)

# Load the dataset
df = pd.read_csv('commands.csv')

# Apply preprocessing to the command column
df['Command'] = df['Command'].apply(preprocess_text)

# Features and labels
X = df['Command']
y = df['Intent']

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create a TF-IDF Vectorizer with bigrams and a limited number of features
vectorizer = TfidfVectorizer(stop_words='english', max_features=1000, ngram_range=(1, 2))

# Create a model pipeline
model = make_pipeline(vectorizer, LogisticRegression(max_iter=1000))

# Use StratifiedKFold to prevent imbalance errors during cross-validation
cv = StratifiedKFold(n_splits=2)

# Perform hyperparameter tuning for the logistic regression model
param_grid = {'logisticregression__C': [0.001, 0.01, 0.1, 1, 10, 100]}
grid_search = GridSearchCV(model, param_grid, cv=cv, n_jobs=-1)
grid_search.fit(X_train, y_train)

# Print best hyperparameters found by GridSearchCV
print(f"Best hyperparameters: {grid_search.best_params_}")
print(f"Best cross-validation score: {grid_search.best_score_}")

# Train the model with the best found parameters
best_model = grid_search.best_estimator_

# Evaluate the model on the test set
y_pred = best_model.predict(X_test)

# Print classification report and confusion matrix
print("Classification Report:")
print(classification_report(y_test, y_pred))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Save the trained model
with open('file_assistant_model.pkl', 'wb') as f:
    pickle.dump(best_model, f)
    

print("✅ Model trained and saved successfully.")
