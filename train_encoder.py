####  This script trains a BERT model for intent classification using the training data provided in the data folder. The model is then evaluated on the test data and saved as a SavedModel to be combined with the decoder for a more robust response. ####

# Imports
import os
import pandas as pd
import numpy as np
import tensorflow as tf
from transformers import TFBertForSequenceClassification, BertTokenizer

# Set random seeds and environment variable for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # Disable OneDNN for better performance

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

# Load and prepare training and validation data 
df_train = pd.read_json("train.json")
df_train = df_train.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
df_validate = pd.read_json("validation.json")
df_validate = df_validate.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

# Map intents to numeric labels 
label_map = {label: idx for idx, label in enumerate(df_train['Intent'].unique())}
df_train['Intent'] = df_train['Intent'].map(label_map)
df_validate['Intent'] = df_validate['Intent'].map(label_map)

# Load pre-trained bert model and tokenizer
model_name = "bert-base-uncased"
tokenizer = BertTokenizer.from_pretrained(model_name)
model = TFBertForSequenceClassification.from_pretrained(model_name, num_labels=len(label_map))

# Tokenize data
train_encodings = tokenizer(df_train["Query"].tolist(), truncation=True, padding=True, max_length=128, return_tensors="tf")
validate_encodings = tokenizer(df_validate["Query"].tolist(), truncation=True, padding=True, max_length=128, return_tensors="tf")

# Create TensorFlow datasets
def create_tf_dataset(encodings, labels):
    return tf.data.Dataset.from_tensor_slices((dict(encodings), labels)).shuffle(len(labels)).batch(8)

train_dataset = create_tf_dataset(train_encodings, df_train["Intent"])
validate_dataset = create_tf_dataset(validate_encodings, df_validate["Intent"])

# Compile and train the model
optimizer = tf.keras.optimizers.Adam(learning_rate=5e-5)
loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
metric = tf.keras.metrics.SparseCategoricalAccuracy('accuracy')

model.compile(optimizer=optimizer, loss=loss, metrics=[metric])
# print(model.summary())
model.fit(train_dataset, validation_data=validate_dataset, epochs=5)


#  Testing the model 
# Load test data
df_test = pd.read_json("test.json")
df_test = df_test.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)  # shuffle

#  same label map created during training
df_test['Intent'] = df_test['Intent'].map(label_map)

# Tokenize test data
test_encodings = tokenizer(df_test["Query"].tolist(), truncation=True, padding=True, max_length=128, return_tensors="tf")

# Create TensorFlow test dataset
test_dataset = create_tf_dataset(test_encodings, df_test["Intent"])

# Evaluate the model on the test dataset
test_loss, test_accuracy = model.evaluate(test_dataset)
print(f"Test Loss: {test_loss}, Test Accuracy: {test_accuracy}") 

# Save the entire model as a SavedModel.
model.save('my_bert_model')

#### END OF CODE ####