# the encoder imports
import tensorflow as tf
from transformers import BertTokenizer

import os

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')

# Set the environment variable
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Load the SavedModel directly for inference
model = tf.saved_model.load('my_bert_model')

# Initialize the tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

####### MODIFICATION 1: Define a function to classify the user's intent and provide more information to the decoder #######
def get_help(query):
    """This function provides more context on the user's query"""
    # Tokenise the input query
    test_encodings = tokenizer(query, truncation=True, padding=True, max_length=128, return_tensors="tf")
    # Perform the inference
    outputs = model(test_encodings)
    # Access the logits
    logits = outputs['logits']  # Shape: (batch_size, num_labels)
    # Get the most likely prediction using argmax
    prediction = tf.argmax(logits, axis=-1)
    # Convert prediction to numpy for easier handling
    predicted_label_index = prediction.numpy()
    # Dictionary mapping indices to labels
    label_map = {
        0: "update_booking",
        1: "delete_a_booking",
        2: "NOTA",
        3: "delete_all_bookings",
        4: "read_booking",
        5: "get_suggestions",
        6: "create_booking"
    }
    # Get the descriptive text label and return to the decoder
    predicted_text_label = label_map.get(predicted_label_index[0], "Unknown Label")
    print(f"Query: {query}, User_Intent: {predicted_text_label}")
    return f"Query: {query}, User_Intent: {predicted_text_label}"