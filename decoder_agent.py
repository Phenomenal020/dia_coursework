import os
import requests

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import wikipedia

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from langchain.agents import  AgentExecutor

from langchain_core.runnables import RunnableConfig

from langchain_community.callbacks.streamlit import (
    StreamlitCallbackHandler,
)

from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)
from langchain.agents import AgentExecutor, create_tool_calling_agent

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder

from dotenv import load_dotenv

import streamlit as st

# Load the environment variables from the .env file
load_dotenv()

def connect(url, server_api_version):
    """Connects to the MongoDB database and returns the database and collection objects if successful. It raises a connection error if not"""
    if not url:
        raise ValueError("MongoDB URL must be provided")
    try:
        server_api = ServerApi(server_api_version)
        client = MongoClient(url, server_api=server_api)
        client.admin.command('ping')  # Ping the server to check connection
        print("Pinged your deployment. You successfully connected to MongoDB!")
        db = client["travel-app"]
        collection = db["bookings"]
        return db, collection
    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")
    
# Establish a connection to the database (MongoDB in this case)
try:
    db_url = os.environ["MONGODB_URL"]
    if not db_url:
        raise EnvironmentError("MONGODB_URL is not set in environment variables")
    db, collection = connect(url = db_url, server_api_version = '1')
except Exception as e:
    print(e)

# tool 1: create_booking
@tool
def create_booking(name: str, destination: str, description: str) -> str:
    """
    Creates a booking in the database based on the user's name and their selection of travel destinations.
    Check if the name starts with 'user' (case insensitive) and asks for the if true.
    Returns a message about the booking creation status.
    """
    # Check if the name starts with 'user' (case insensitive)
    if name.strip().lower().startswith('user'):
        return "Please provide a specific name, not a generic identifier starting with 'user'."

    booking = {
        "username": name,
        "destination": destination,
        "description": description
    }
    try:
        # Attempt to insert the booking into the database
        result = collection.insert_one(booking)
        return "Booking created successfully!"
    except Exception as e:
        # Handle any errors during the database operation
        return f"Error: {str(e)}"

# tool 2: read_booking
@tool
def read_booking(name):
    """Retrieves all bookings that match the given user name from the MongoDB database. If there are no bookings with the user's name, it returns an error. Make sure the user's name is known."""
    try:
        documents = collection.find({"username": name})
        document_list = list(documents)
        return document_list
    except Exception as e:
        return {"error": str(e)}

# tool 3: update_booking
@tool
def update_booking(name, destination=None, description=None):
    """Updates a booking document in the MongoDB collection based on the user's name. It updates the destination field if the user already has a booking. If no existing booking is found, it creates a new document. Make sure the user's name is known. Also make sure the destination or description is known. If not known, ask them to provide the destination or description. If the user has multiple bookings, ask them to specify the destination or activity to update. Finally, call get_suggestion to get an appropriate suggestion for the updated entries"""
    try:
        if not destination and not description:
            return "No changes made to the booking."
        elif not destination:
            update_document = {
                "$set": { "description": description }
            }
        elif not description:
            update_document = {
                "$set": { "destination": destination }
            }
        result = collection.update_one({'username': name}, update_document, upsert=True)
        if result.matched_count: 
            return "Booking updated successfully!"
        elif result.upserted_id:
            return f"New booking created with ID: {result.upserted_id}"
        else:
            return "No changes made to the booking."
    except Exception as e:
        return {"error": str(e)}

# tool 4: delete_a_booking
@tool
def delete_a_booking(name, destination):
    """Deletes a booking in the MongoDB collection based on the user's name. It returns an error if the deletion fails. Make sure the user's name and the destination or activity is known. If the user has multiple bookings, ask them to specify the destination or activity to delete"""
    try:
        result = collection.delete_one({'username': name, destination: destination})
        return "Booking deleted successfully!"
    except Exception as e:
        return {"error": str(e)}
    
# tool 5: delete_all_bookings
@tool
def delete_all_bookings(name):
    """Deletes every booking in the MongoDB collection based on the user's name. This should clear the bookings for a user. It returns an error if the deletion fails. Make sure the user's name is known. ask them again if they are sure they want to delete all their bookings before proceeding. If they confirm, delete all their bookings. If they don't confirm, do nothing."""
    try:
        result = collection.delete_many({'username': name})
        return "All bookings deleted successfully!"
    except Exception as e:
        return {"error": str(e)}

# helper function to search for a place on Wikipedia
def wiki_search(place_name):
    """Fetches a description of a place from Wikipedia. If the place is not found, it returns an error message. If the place is ambiguous, it returns a list of options."""
    wikipedia.set_lang('en')
    try:
        summary = wikipedia.summary(place_name, sentences=1)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Disambiguation page found. Please specify one of these options: {', '.join(e.options)}"
    except wikipedia.exceptions.PageError:
        return f"No description available for {place_name}"

# tool 6: get_suggestions
@tool
def get_suggestions(place):
    """Gets suggestions for interesting things to do or interesting places to visit given the user's input. Use this function whenever you want to provide recommendations to the user for a plcae or activity. call this function as get_suggestions(self, place: place) where self  is the recommendation agent and place is the place or activity for which you want to get recommendations."""
    search_url = "https://api.content.tripadvisor.com/api/v1/location/search"
    key = os.environ["TRIP_ADVISOR_KEY"]
    params = {
        'key': key,
        'searchQuery': place,
        'category': 'attractions',
        'language': 'en'
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        data = response.json()
        recommendations = []
        for item in data.get('data', []):
            name = item.get('name')
            description = wiki_search(name)
            recommendations.append(f"Name: {name}: ### Description: {description}")
        return "\n".join(recommendations)
    else:
        return "Failed to retrieve recommendations."

# tools available for the agent to call
tools = [
    get_suggestions,
    create_booking,
    read_booking,
    update_booking,
    delete_a_booking,
    delete_all_bookings,
]

#  ------------------------------------- Environment  
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [] # Initialize chat history if it doesn't exist

# Set page configuration
st.set_page_config(page_title="LangChain: Travel Advisor Agent", page_icon="🎧")
st.title("🎧 Travel Advisor Agent") 

# Input for API key
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# Chat message history and conversation memory setup
msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history", chat_memory=msgs)

# ---------------------------------------- The agent
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a travel agent that recommends travel destinations to users and helps them make a list of interesting places and activities to do. You are helpful but sassy. Also, engage in small talk where possible but try to keep the conversation focused on making a list of travel destinations and activities for the user. Before calling the get_suggestion function, make sure to ask the user for their name. Likewise for other functions, make sure you already know the user's name not something generic like 'user' or 'user123'. It is very important to know the user's name before making entries to the database as this would be used to connect to the database. Before you make a booking, make sure their is an appropriate description field. Also, do not hallucinate. If you do not have enough information to make a recommendation, ask the user for more information. Always make sure to confirm with the user before making any interactions with the database. If you are not sure, ask the user for clarification. Finally, whenever you update an existing booking's destination or description fields, check to make sure they match. If they are not similar, call get_suggestions function to get an appropriate suggestion for the updated entries' destination or description field as the case may be. Note that based on what is being updated - name, description or destination, the call to get_suggestion may or may not be required. For security reasons, make sure to only show the user their own bookings. If a user named Stephen asks for Angela's bookings, decline the request."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# ---------------------------------------- Actions
# Reset chat history
if len(msgs.messages) == 0 or st.sidebar.button("Reset chat history"):
    msgs.clear()
    msgs.add_ai_message("Hello, I am your travel agent. How can I help you?")
    st.session_state.steps = {}

# Render chat messages
avatars = {"human": "user", "ai": "assistant"}
for idx, msg in enumerate(msgs.messages):
    with st.chat_message(avatars[msg.type]):
        for step in st.session_state.steps.get(str(idx), []):
            if step[0].tool == "_Exception":
                continue
            with st.status(f"**{step[0].tool}**: {step[0].tool_input}", state="complete"):
                st.write(step[0].log)
                st.write(step[1])
        st.write(msg.content)

# Handling user input
if prompt := st.chat_input(placeholder="Ask me to recommend a place or activity or update a booking for you."):
    st.chat_message("user").write(prompt)
    # API key check
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()
    
    # Setting up model and agent
    model = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key, streaming=True)
    agent = create_tool_calling_agent(llm=model, tools=tools, prompt=agent_prompt)
    executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, memory=memory, return_intermediate_steps=True, handle_parsing_errors=True)
    
    with st.chat_message("assistant"):
        st_cb = StreamlitCallbackHandler(st.container(), expand_new_thoughts=False)
        cfg = RunnableConfig(callbacks=[st_cb])
        print("Prompt: ", prompt)
        print(type(prompt))
        response = executor.invoke({"input": prompt}, cfg)
        st.write(response["output"])
        st.session_state.steps[str(len(msgs.messages) - 1)] = response["intermediate_steps"]
        
#### END OF CODE ####