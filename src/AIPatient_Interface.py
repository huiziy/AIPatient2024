import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import time
from neo4j import GraphDatabase
from streamlit_chat import message
from py2neo import Graph, Node as Py2neoNode, Relationship as Py2neoRelationship
from streamlit_agraph import agraph, Node, Edge, Config
from Agent import Agents
from Neo4j_functions import Neo4jDatabase
from Neo4j_visualizer import Neo4jGraphVisualizer
import random
import logging
import os

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('interactive_session.log'), logging.StreamHandler()])

# SECRET_FILE ="/content/drive/MyDrive/secrets.txt"

## Generate personality profiles
personality_profiles = [
    ["Responsible", "Organized", "Analytical"],
    ["Anxious", "Detailed", "Inquisitive"],
    ["Optimistic", "Outgoing", "Cooperative"],
    ["Pessimistic", "Reserved", "Skeptical"],
    ["Energetic", "Impulsive", "Adventurous"],
    ["Caring", "Patient", "Empathetic"],
    ["Practical", "Stoic", "Independent"],
    ["Emotional", "Trusting", "Open"]
]

def main():
    # Initialize the session state for holding the conversation if it doesn't exist
    if 'conversation' not in st.session_state:
        st.session_state.conversation = []

    # Set up welcome message at the beginning of the session
    # if not st.session_state.conversation:
    #     message("Welcome to AIPatient: A Virtual Patient for Medical Education")

    # Load necessary credentials and set up the database connection

    uri = "neo4j+s://be1f494b.databases.neo4j.io"
    user = "neo4j"
    password = "<database password>"
    db = Neo4jDatabase(uri, user, password)
    model_type = "claude"
    verbose = False
    test_run = True

    # Initiate the agents for the conversation
    try:
        secret_file = "/Users/huiziyu/Dropbox/secrets.txt"
        agents = Agents(secret_file, db, model_type)
    except:
        secret_file = "../secrets.txt"
        agents = Agents(secret_file, db, model_type)

    # Check if a patient admission is already stored in session state, if not, get a new one
    if 'patient_admission' not in st.session_state:
        ## Demo run
        if test_run:
            patient_admission = {
                'SubjectID': 17546, 
                'AdmissionID': 190044  
            }
        else:
            patient_admission = db.get_random_patient_admission()
        st.session_state.patient_admission = patient_admission
        st.session_state.graph_generated = False
        ## Demo Run
        if test_run:
            st.session_state.personality_profile = ["Responsible", "Organized", "Analytical","Terse"]
        else:
            if verbose:
                st.session_state.personality_profile = random.choice(personality_profiles) + ["Verbose"]
            else:
                st.session_state.personality_profile = random.choice(personality_profiles) + ["Terse"]
        st.session_state.model = model_type
        st.session_state.conversation_history = f"The patient has ID {patient_admission['SubjectID']}, and the admission ID {patient_admission['AdmissionID']}"
        logging.info(f"New patient drawn: {patient_admission['SubjectID']}")

    patient_admission = st.session_state.patient_admission
    personality_profile = st.session_state.personality_profile

    # Generate the graph if it hasn't been generated yet
    if not st.session_state.graph_generated:
        visualizer = Neo4jGraphVisualizer(uri, user, password)
        results = visualizer.fetch_data(int(patient_admission['AdmissionID']))
        nodes, edges = visualizer.create_nodes_edges(results)
        st.session_state.nodes = nodes
        st.session_state.edges = edges
        st.session_state.graph_generated = True
        logging.info("Graph generated and stored in session state.")

    # Create two columns for QA and Knowledge Graph
    col1, col2 = st.columns(2)

    with col1:
        st.header("QA Interaction")
        # Display the previous conversations
        chat_placeholder = st.empty()
        agents.display_conversation(chat_placeholder)

        # Input for new queries from the doctor
        user_input = st.text_input("Enter your query as a doctor:", key="doctor_query")

        # Submit button to process the query
        if st.button("Submit"):
            if user_input.lower() == 'exit':
                st.write("Terminating session.")
                db.close()
                return

            # Process the interaction
            patient_response, updated_conversation_history = agents.interactive_session(db, user_input, st.session_state.conversation_history, patient_admission, personality_profile)

            # Update the chat display and the session state
            st.session_state.conversation.append((user_input, patient_response))
            st.session_state.conversation_history = updated_conversation_history

            # Refresh the chat display to include the new conversation
            agents.display_conversation(chat_placeholder)
        
    with col2:
        st.header("Session Info")
        #st.markdown("#### Patient ID")
        #st.write(st.session_state.patient_admission[0])
        #st.markdown("#### Admission Personality")
        #st.write(st.session_state.patient_admission[1])
        st.markdown("#### Large Language Model")
        st.write("Claude 3.5 Sonnet")
        st.markdown("#### Patient Personality")
        st.write(", ".join(st.session_state.personality_profile))
        st.header("Converstion Summary")
        st.write(st.session_state.conversation_history)

        st.header("Electronic Health Records Knowledge Graph")
        # Fetch and visualize the knowledge graph only if it hasn't been generated yet
        visualizer = Neo4jGraphVisualizer(uri, user, password)
        visualizer.visualize_graph(st.session_state.nodes, st.session_state.edges)


    # Close the database connection when done
        db.close()

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    st.title("AIPatient Interface")
    st.text("Welcome to AIPatient: A Virtual Patient for Medical Education")
    main()