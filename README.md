# DIA Coursework Application 
## How well does a decoder-only agent like GPT-3.5 handle user queries with different levels of proficiency in a conversational chatbot? 

## Does adding an encoder like BERT to the pipeline improve the agent’s performance? 

This README provides instructions on how to set up and run the application.

## Prerequisites

- Python
- [Streamlit](https://streamlit.io/)
- [OpenAI API key](https://openai.com/)

## Setup Instructions

### 1. Create a Virtual Environment
You can create a virtual environment to manage dependencies:
- python -m venv venv
- source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

Alternatively, if you need to install pip, run:
- curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
- python get-pip.py

### 2. Install Required Packages
Install the necessary packages by running:
- pip install -r requirements.txt

### 3. Setup API Keys - MongoDB, Trip advisor, and OpenAI
- Add to a .env file to be used for connecting to these platforms.
- Copy the OpenAI api key and paste in the sidebar

### 4. Train the Encoder 
Note: Due to size constraints, the BERT model is not included in this repo. To use this, run the following command to train the encoder for inference:
- python train_encoder.py

### 5. Run the Application
To chat with the decoder-only agent:
- streamlit run decoder_agent.py

To chat with the seq2seq (encoder-decoder) agent:
- streamlit run encoder_decoder_agent.py
