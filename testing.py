import os  # built-in module to get environment variables from the OS
from langchain_openai import ChatOpenAI  # from the langchain community package

from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()


# --------------------------------------------- Basic LLM Chain -----------------------------------------------------
llm = ChatOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# simple test to check if the API key is working
# resp = llm.invoke("Hello, how are you?")
# print(resp)

# More guided test to check if the API key is working
from langchain_core.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are world class technical documentation writer."),
#     ("user", "{input}"),
# ])
# chain = prompt | llm   # chaining the prompt and the language model
# resp = chain.invoke({"input": "how can langsmith help with testing?"})
# print(resp)

# However, the output is a message that is not so convenient to work with
# To convert the output to a string, we need an output parser
# from langchain_core.output_parsers import StrOutputParser
# output_parser = StrOutputParser()

# chain = prompt | llm | output_parser  # chaining the prompt, language model, and output parser
# resp = chain.invoke({"input": "how can langsmith help with testing?"})
# print(resp)

# TODO: Deepdive @ https://python.langchain.com/docs/modules/model_io/


# ----------------------------------------------------- Retrieval -----------------------------------------------------
# To properly answer the original question ("how can langsmith help with testing?"), we need to provide additional context to the LLM. We can do this via retrieval. Retrieval is useful when you have too much data to pass to the LLM directly. You can then use a retriever to fetch only the most relevant pieces and pass those in.

# Note:  A Retriever can be backed by anything - a SQL table, the internet, etc - but in this instance we will populate a vector store and use that as a retriever.
# TODO: More on Vector stores and retrieval: https://python.langchain.com/docs/modules/data_connection/vectorstores/

# ---------------> First, we need to load the data that we want to index
from langchain_community.document_loaders import WebBaseLoader
loader = WebBaseLoader("https://docs.smith.langchain.com/user_guide")
docs = loader.load()

# --------------->  Next, we need to index it into a vectorstore
# TODO: Embedding models in Langchian: https://python.langchain.com/docs/modules/data_connection/text_embedding/
# Use the embedding of the LLM
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings()

# --------------> Before saving to the vector db, we need to split the text into documents
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter()
documents = text_splitter.split_documents(docs)
vector = FAISS.from_documents(documents, embeddings)

# TODO: more on FAISS: https://python.langchain.com/docs/integrations/vectorstores/faiss/
# TODO: more on Google vertex ai vector search: https://python.langchain.com/docs/integrations/vectorstores/google_vertex_ai_vector_search/

# Now that we have this data indexed in a vectorstore, we will create a retrieval chain. This chain will take an incoming question, look up relevant documents, then pass those documents along with the original question into an LLM and ask it to answer the original question.

# --------------------> To use the document retirval, set up a chain for it with a well defined prompt template
from langchain.chains.combine_documents import create_stuff_documents_chain
prompt = ChatPromptTemplate.from_template("""Answer the following question based only on the provided context:
<context>
{context}
</context>
Question: {input}""")
document_chain = create_stuff_documents_chain(llm, prompt)


# if we wanted to, we could pass in out documents directly
# from langchain_core.documents import Document
# document_chain.invoke({
#     "input": "how can langsmith help with testing?",
#     "context": [Document(page_content="langsmith can let you visualize test results")]
# })

# However, we want the documents to first come from the retriever we just set up. That way, we can use the retriever to dynamically select the most relevant documents and pass those in for a given question.
# ----------------->  so,
from langchain.chains import create_retrieval_chain
retriever = vector.as_retriever()
# retrieval_chain = create_retrieval_chain(retriever, document_chain)

# # We can now invoke this chain. This returns a dictionary - the response from the LLM is in the answer key
# response = retrieval_chain.invoke({"input": "how can langsmith help with testing?"})
# print(response["answer"])

# TODO: Dive deeper into retrieval in Langchain: https://python.langchain.com/docs/modules/data_connection/


# ----------------------------------------------- Conversational Retrieval Chain -------------------------------------
# The chain we've created so far can only answer single questions. One of the main types of LLM applications that people are building are chat bots. So how do we turn this chain into one that can answer follow up questions?

# Adjustments
# 1.    The retrieval method should now not just work on the most recent input, but rather should take the whole history into account.
# 2.    The final LLM chain should likewise take the whole history into account

# In order to update retrieval, we will create a new chain. This chain will take in the most recent input (input) and the conversation history (chat_history) and use an LLM to generate a search query.

from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder

# First we need a prompt that we can pass into an LLM to generate this search query
prompt = ChatPromptTemplate.from_messages([
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    ("user", "Given the above conversation, generate a search query to look up to get information relevant to the conversation")
])
retriever_chain = create_history_aware_retriever(llm, retriever, prompt)

# We can test this out by passing in an instance where the user asks a follow-up question.
from langchain_core.messages import HumanMessage, AIMessage
# chat_history = [HumanMessage(content="Can LangSmith help test my LLM applications?"), AIMessage(content="Yes!")]
# resp = retriever_chain.invoke({
#     "chat_history": chat_history,
#     "input": "Tell me how"
# })
# print(resp)

# prompt = ChatPromptTemplate.from_messages([
#     ("system", "Answer the user's questions based on the below context:\n\n{context}"),
#     MessagesPlaceholder(variable_name="chat_history"),
#     ("user", "{input}"),
# ])
# document_chain = create_stuff_documents_chain(llm, prompt)
# retrieval_chain = create_retrieval_chain(retriever_chain, document_chain)

# chat_history = [HumanMessage(content="Can LangSmith help test my LLM applications?"), AIMessage(content="Yes!")]
# retrieval_chain.invoke({
#     "chat_history": chat_history,
#     "input": "Tell me how"
# })



# ---------------------------------------------------- Agents ----------------------------------------------------------
# NOTE: for this example we will only show how to create an agent using OpenAI models, as local models are not reliable enough yet.
# TODO: More on Agents: https://python.langchain.com/docs/modules/agents/

# We've so far created examples of chains - where each step is known ahead of time. The final thing we will create is an agent - where the LLM decides what steps to take.

from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.agents import create_openai_functions_agent
from langchain.agents import AgentExecutor

# search tool
from langchain_community.tools.tavily_search import TavilySearchResults
search = TavilySearchResults(api_key=os.environ.get("TAVILY_API_KEY"))

# retriever tool
from langchain.tools.retriever import create_retriever_tool
retriever_tool = create_retriever_tool(
    retriever,
    "langsmith_search",
    "Search for information about LangSmith. For any questions about LangSmith, you must use this tool!",
)

# tools list to pass into the agent
tools = [retriever_tool, search]

# Get the prompt to use - you can modify this!
prompt = hub.pull("hwchase17/openai-functions-agent")

# You need to set OPENAI_API_KEY environment variable or pass it as argument `api_key`.
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=os.environ.get("OPENAI_API_KEY"))

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# agent_executor.invoke({"input": "how can langsmith help with testing?"})
agent_executor.invoke({"input": "what is the weather in SF?"})


# TODO: LangServe