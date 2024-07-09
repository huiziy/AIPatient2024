import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import time
from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError
from streamlit_chat import message
from py2neo import Graph, Node as Py2neoNode, Relationship as Py2neoRelationship
from streamlit_agraph import agraph, Node, Edge, Config
from Neo4j_functions import Neo4jDatabase
import logging
import os
import re
from anthropic import Anthropic
from anthropic import AnthropicBedrock


class Agents:
    def __init__(self, secret_file, db, model_type):
        self.anthropic_client = self.load_anthropic_client(secret_file)
        self.model_type = model_type.lower()

        self.db = db

        self.node_properties_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
            WITH label AS nodeLabels, collect(property) AS properties
            RETURN {labels: nodeLabels, properties: properties} AS output
            """

        self.rel_properties_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
            WITH label AS nodeLabels, collect(property) AS properties
            RETURN {type: nodeLabels, properties: properties} AS output
            """

        self.rel_query = """
            CALL apoc.meta.data()
            YIELD label, other, elementType, type, property
            WHERE type = "RELATIONSHIP" AND elementType = "node"
            RETURN {source: label, relationship: property, target: other} AS output
            """
    
    def load_anthropic_client(self, secret_file):
        with open(secret_file) as f:
            lines = f.readlines()
            for line in lines:
                if line.split(',')[0].strip() == "Access_key_ID":
                    Access_Key = line.split(',')[1].strip()
                if line.split(',')[0].strip() == "Secret_access_key":
                    Secret_Key = line.split(',')[1].strip()
        return AnthropicBedrock(aws_access_key=Access_Key,aws_secret_key=Secret_Key,aws_region="us-east-1",
)

    def run_claude(self, text_prompt, max_tokens_to_sample=3000, model="anthropic.claude-3-5-sonnet-20240620-v1:0"):
        message = self.anthropic_client.messages.create(
            max_tokens=max_tokens_to_sample,
            messages=[
                {"role": "user", "content": text_prompt}
            ],
            model=model,
        )
        extracted_texts = [block.text for block in message.content]
        return extracted_texts[0]
        
    ## Running appropriate models
    def run_model(self, text_prompt, max_tokens_to_sample=4096, temperature=0):
        return self.run_claude(text_prompt, max_tokens_to_sample)

    def schema_text(self, node_props, rel_props, rels):
        return f"""
            This is the schema representation of the Neo4j database.
            Node properties are the following:
            {node_props}

            Relationship properties are the following:
            {rel_props}

            Relationship point from source to target nodes
            {rels}

            Make sure to respect relationship types and directions
            """
            
    def generate_schema(self):
        node_props = self.db.execute_cypher_query(self.node_properties_query)
        rel_props = self.db.execute_cypher_query(self.rel_properties_query)
        rels = self.db.execute_cypher_query(self.rel_query)
        return self.schema_text(node_props, rel_props, rels)
    
    # Edge and node extraction
    def relationship_extraction_prompt(self, conversation_history, text, patient_admission):
        subject_id = patient_admission['SubjectID']
        hadm_id = patient_admission['AdmissionID']
        schema = self.generate_schema()
        prompt = f"""
        
        Based on the doctor's query, first determine what the doctor is asking for. Then extract the appropriate relationship and nodes from the knowledge graph. \n
        For admissions related queries, the query should focus on "HAS_ADMISSION" relationship and "Admission" node. \n
        For patient information related queries, the query should focus on the "Patient" node. \n
        If the doctor asked about a symptom (e.g. cough, fever, etc.), the query should check if the "symptom" node and the "HAS_SYMPTOM" or "HAS_NOSYMOTOM" relationship; \n
        If the doctor asked about the duration, frequency, and intensity of a symptom, the query should first check if the symptom exist. If it exist, then check the "duration", "frequency" and "intensity" node respectively, and "HAS_DURATION", "HAS_FREQUENCY", "HAS_INTENSITY" relationship respectively. \n
        If the doctor asked about medical history, the query should check "History" node and the HAS_MEDICAL_HISTORY relationship. \n
        If the doctor asked about vitals (temperature, blood pressure etc), the query should check the "Vital" node and "HAS_VITAL" relationship. \n
        If the doctor asked about social history (smoking, alcohol consumption etc), the query should check the "SocialHistory" node and "HAS_SOCIAL_HISTORY" relationship. \n
        If the doctor aksed about family history, the query should first check the "HAS_FAMILY_MEMBER" relationship and "FamilyMember" node. Then, the query should check the "HAS_MEDICAL_HISTORY" relationship and "FamilyMedicalHistory" node associated with the "FamilyMember" node. \n 
        Output_format: Enclose your output in the following format. Do not give any explanations or reasoning, just provide the answer. For example:
        {{'Nodes': ['symptom', 'duration'], 'Relationships': ['HAS_SYMPTOM', 'HAS_DURATION']}}
        
        The natural language query is:
        {text}
        
        The previous conversation history is:
        {conversation_history}
        
        
        The Knowledge Graph Schema is:
        {schema}
        """
        
        return prompt
        

    def cypher_query_construction_prompt(self, conversation_history, text, patient_admission, nodes_edges, abstraction_context = None):
        subject_id = patient_admission['SubjectID']
        hadm_id = patient_admission['AdmissionID']
        schema = self.generate_schema()
        prompt = f"""
        Write a cypher query to extract the requested information from the natural language query. The SUBJECT_ID is {subject_id}, and the HADM_ID is {hadm_id}.
        The nodes and edges the query should focus on are {nodes_edges} \n
        Note that if the doctor's query is vague, it should be referring to the current context.\n
        The Cypher query should be case insensitive and check if the keyword is contained in any fields (no need for exact match). \n
        The Cypher query should handle fuzzy matching for keywords such as 'temperature', 'blood pressure', 'heart rate', etc., in the LABEL attribute of Vital nodes.\n
        The Cypher query should also handel matching smoke, smoking, tobacco if asked about smoking and social history; similarly for drinking, or alcohol. \n
        Only return the query as it should be executable directly, and no other text. Don't include any new line characters, or back ticks, or the word 'cypher', or square brackets, or quotes.\n
        
        The previous conversation history is:
        {conversation_history}
        
        The natural language query is:
        {text}
        
        The Knowledge Graph Schema is:
        {schema}"""

        if abstraction_context is not None:
            prompt += f"""
            The step back context is:
            {abstraction_context} 
        """

        prompt += """
        Here are a few examples of Cypher queries, you should replay SUBJECT_ID and HADM_ID based on input:\n
        Example 1: To check if the patient has seizures as a symptom, the cypher query should be: 
        MATCH (p:Patient {{SUBJECT_ID: 23709}})
        OPTIONAL MATCH (p)-[:HAS_ADMISSION]->(a:Admission {{HADM_ID: 182203}})-[:HAS_SYMPTOM]->(s:Symptom)
        WHERE s.name =~ '(?i).*seizure.*'
        WITH p, a, s
        OPTIONAL MATCH (p)-[:HAS_ADMISSION]->(a)-[:HAS_NOSYMPTOM]->(ns:Symptom)
        WHERE ns.name =~ '(?i).*seizure.*'
        RETURN 
        CASE 
            WHEN s IS NOT NULL THEN 'HAS seizure'
            WHEN ns IS NOT NULL THEN 'DOES NOT HAVE seizures'
            ELSE 'DONT KNOW'
        END AS status

        Example 2: To check how long has the patient had fevers as a symptom, the cypher query should be:
        MATCH (p:Patient {{SUBJECT_ID: 23709}})
        OPTIONAL MATCH (p)-[:HAS_ADMISSION]->(a:Admission {{HADM_ID: 182203}})-[:HAS_SYMPTOM]->(s:Symptom)
        WHERE s.name =~ '(?i).*fever.*'
        WITH p, a, s
        OPTIONAL MATCH (s)-[:HAS_DURATION]->(d:Duration)
        RETURN 
        CASE 
            WHEN s IS NULL THEN 'DOES NOT HAVE fevers'
            WHEN d IS NULL THEN 'DONT KNOW'
            ELSE d.name
        END AS fever_duration

        Example 3: To check for family history, the cupher query should be: 
        MATCH (p:Patient {{SUBJECT_ID: 23709}})-[:HAS_FAMILY_MEMBER]->(fm:FamilyMember)
        OPTIONAL MATCH (fm)-[:HAS_MEDICAL_HISTORY]->(fmh:FamilyMedicalHistory)
        RETURN fm.name AS family_member, fmh.name AS medical_history
        
        """
        return prompt
    
    ## Helper function: format cypher query
    def clean_cypher_query(self, query):
        # Remove surrounding quotes
        query = query.strip('"')
        # Remove surrounding brackets
        query = query.strip('[]')
        # Remove newline characters
        query = query.replace('\\n', ' ')
        # Remove any leading or trailing whitespace characters
        query = query.strip()
        # Normalize whitespace within the query
        query = re.sub(r'\s+', ' ', query)
        return query
    
    ## Abstraction with a Few Shot Examples
    def abstraction_generation_prompt(self, conversation_history, text):
        prompt = f"""
        You are an AI and Medical EHR expert. Your task is to step back and paraphrase a question to a more generic step-back question, which is easier to use for cypher query generation. \n 
        If the question is vague, consider the conversation history and the current context. Do not give any explanations or reasoning, just provide the answer. 
        Here are a few examples: \n
        input: Do you have fevers as a symptom? \n
        output: What symptoms does the patient has? \n
        input: Is your current temperature above 97 degrees? \n
        output: What is the patient's temperature? \n
        
        The current conversation history is:
        {conversation_history}
        The original query is:
        {text}
        """
        return prompt
    
    ## Rewrite Query Result Function
    ## This function combines the query results, and relationship to convert it to natural language
    def query_result_rewrite(self, doctor_query, cypher_query, query_result):
        prompt = f"""
        You are a doctor's assistant. Based on the cypher_query, please structure the retrieved query results into natural language. Include all subject, relationship and object. 
        For example: \n
        doctor query: what symptoms do you have?
        cypher query: MATCH (p:Patient)-[:HAS_ADMISSION]->(a:Admission {{HADM_ID: 182203}})
        MATCH (a)-[:HAS_SYMPTOM]->(s:Symptom)
        WHERE p.SUBJECT_ID = 23709
        RETURN s.name AS Symptom 

        retrieved result: ['black and bloody stools', 'lightheadedness', 'shortness of breath']

        output: The patient has symptoms of black and bloody stools, lightheadedness, shortness of breath. 

        The doctor's original query is:
        {doctor_query}
        The cypher query is:
        {cypher_query}
        The retrieved results are:
        {query_result}
        """

        return prompt


    ## Summarization Function
    def summarize_text_prompt(self, conversation_history, doctor_query, patient_response):
        prompt = f"""
        You are the doctor's assistent responsible for summarizing the conversation between the doctor and the patient.
        Be very brief, include the all the conversation history, doctor and patient's query and response. The last sentence should be about the current context (e.g. vital, symptom, or history).
        Write in full sentences and do not fabricate symptoms or history.
        The previous conversation is as follows:
        {conversation_history}
        The doctor has asked about the following query:
        {doctor_query}
        The patient's response to the doctor's query:
        {patient_response}
        """
        return prompt

    ## Rewrite Function
    def rewrite_response_prompt(self, conversation_history, doctor_query, query_result, patient_admission, personality):
        subject_id = patient_admission['SubjectID']
        hadm_id = patient_admission['AdmissionID']
        prompt = f"""
        You are a virtual patient in an office visit. Your personality is {personality}.
        Your conversation history with the doctor is as follows:
        {conversation_history}
        The doctor has asked about the following query, focusing on the current context (e.g. vital, symptom, or history):
        {doctor_query}
        The query result is:
        {query_result}
        Based on all above information, please write your response to the doctor following your personality traits. Note that if the doctor's query is vague, it should be referring to the current context.
        If the query result is empty, return 'I don't know.' DO NOT fabricate any symptom or medical history. DO NOT add non-existent details to the response. DO NOT inclue any quotes, write in first person perspective. 
        """
        return prompt

    ## Checker Function
    def checker_construction_prompt(self, doctor_query, query_result, conversation_history):
        """
        This function check if the query result is appropirately answered the question, if not, the checker will rewrite the doctor's query and try to generate the cypher query again.
        The checker will try 3 times until it stops and claim the query is not answered. and return "I don't know".
        """
        prompt = f"""
        You are a doctor's assistant. You are recording and evaluating patient's responses to doctor's query.
        The conversation history between the doctor and patient is as follows:
        {conversation_history}
        The doctor's query is:
        {doctor_query}
        The query result is:
        {query_result}
        Based on the above conversation, determine if the patient's response is an appropriate answer to the doctor's query.
        If so, return 'Y' and do not return anything else; if not, rewrite the doctor's query based on the current context; only return the modified query and nothing else.
        """
        return prompt

    ## Design Interface
    def interactive_session(self, db, doctor_query, conversation_history, patient_admission, personality_profile, max_token = 4096):
        if doctor_query.lower() == 'exit':
            logging.info("Session terminated by the user.")
            return "Session terminated by the user."
        
        #########################################################################################################################
        
        ## Step 2.1: Extract relevant nodes and edges
        logging.info("Extract relevant nodes and edges based on query.")
        nodes_edges_query_cypher_prompt = self.relationship_extraction_prompt(conversation_history, doctor_query, patient_admission)
        if len(nodes_edges_query_cypher_prompt) > max_token:
            nodes_edges_query_cypher_prompt = nodes_edges_query_cypher_prompt[:max_token]
        nodes_edges_results = self.run_model(nodes_edges_query_cypher_prompt)
        logging.info(f"Nodes and edges extracted: {nodes_edges_results}")

        ## Step 1: Construct Abstraction Query Prompt
        logging.info("Step 1: Constructing Abstraction Cypher query prompt based on the doctor's query.")
        abstraction_query_prompt = self.abstraction_generation_prompt(conversation_history, doctor_query)
        if len(abstraction_query_prompt) > max_token:
            abstraction_query_prompt = abstraction_query_prompt[:max_token]
        abstraction_query_nl = self.run_model(abstraction_query_prompt)
        logging.info(f"Abstraction query in natural language generated: {abstraction_query_nl}")

        ## Step 3: Generate Abstraction Cypher Query
        logging.info("Constructing Cypher query prompt based on the abstraction query.")
        abstraction_query_cypher_prompt = self.cypher_query_construction_prompt(conversation_history, abstraction_query_nl, patient_admission, nodes_edges_results)
        if len(abstraction_query_cypher_prompt) > max_token:
            abstraction_query_cypher_prompt = abstraction_query_cypher_prompt[:max_token]
        abstraction_query_cypher = self.run_model(abstraction_query_cypher_prompt)
        logging.info(f"Abstraction cypher generated: {abstraction_query_cypher}")
        
        ## Step 3.5: Clean Cypher Query
        abstraction_query_cypher = self.clean_cypher_query(abstraction_query_cypher)

        ## Step 4: Execute the generated Cypher query
        logging.info("Step 4: Executing the generated Cypher query.")
        abstraction_result = db.execute_cypher_query(abstraction_query_cypher)
        if abstraction_result:
            ## Rewrite to natural language
            abstraction_result_rewrite_prompt = self.query_result_rewrite(abstraction_query_nl, abstraction_query_cypher, abstraction_result)
            abstract_result = self.run_model(abstraction_result_rewrite_prompt)
        
        logging.info(f"Abstraction Query result: {abstraction_result}")

        #########################################################################################################################

        ## Step One: Original doctor's query
        logging.info(f"Step Zero: The doctors has asked about: {doctor_query}")
        logging.info("Step One: Constructing Cypher query prompt based on the doctor's query.")
        cypher_query_prompt = self.cypher_query_construction_prompt(conversation_history, doctor_query, patient_admission, nodes_edges_results, abstraction_context=abstraction_result)

        ## Step 2.2: Construct Cypher Query
        if len(cypher_query_prompt) > max_token:
            cypher_query_prompt = cypher_query_prompt[:max_token]
            logging.info(f"Cypher query prompt truncated to {max_token} characters.")
        cypher_query = self.run_model(cypher_query_prompt)
        logging.info(f"Cypher query generated: {cypher_query}")
        
        ## Step 2.3: Clean Cypher Query
        cypher_query = self.clean_cypher_query(cypher_query)

        ## Step Three: Execute the generated Cypher query
        logging.info("Step Three: Executing the generated Cypher query.")
        query_result = db.execute_cypher_query(cypher_query)
        if query_result:
            ## Rewrite to natural language
            query_result_rewrite_prompt = self.query_result_rewrite(doctor_query, cypher_query, query_result)
            query_result = self.run_model(query_result_rewrite_prompt)
        logging.info(f"Query result: {query_result}")

        ## Step Four: Evaluate if the query properly answered the question
        for attempt in range(2):
            logging.info(f"Attempt {attempt + 1}: Evaluating the query result.")
            checker_prompt = self.checker_construction_prompt(doctor_query, query_result, conversation_history)
            if len(checker_prompt) > max_token:
                checker_prompt = checker_prompt[:max_token]
                logging.info(f"Checker prompt truncated to {max_token} characters.")
            checked_result = self.run_model(checker_prompt)
            logging.info(f"Checked result: {checked_result}")

            ## If the answer is deemed appropriate, stop the loop
            if checked_result.strip() == 'Y':
                logging.info("Checked result is appropriate. Breaking the loop.")
                break

            ## If the answer is deemed inappropriate, restructure the question and try again
            logging.info("Checked result is inappropriate. Restructuring the question.")
            cypher_query_prompt = self.cypher_query_construction_prompt(conversation_history, checked_result, patient_admission, nodes_edges_results)
            if len(cypher_query_prompt) > max_token:
                cypher_query_prompt = cypher_query_prompt[:max_token]
                logging.info(f"Cypher query prompt truncated to {max_token} characters.")
            cypher_query = self.run_model(cypher_query_prompt, temperature=attempt)
            query_result = db.execute_cypher_query(cypher_query)
            query_result = self.query_result_rewrite(doctor_query, cypher_query, query_result)
            logging.info(f"New query result: {query_result}")
            # if not query_result or len(query_result) == 0:
            #     query_result = ["I don't know"]
            #     logging.info("No appropriate answer after restructuring. Setting query result to 'I don't know'.")
            #     break

        ## If after three rounds, still no appropriate answer, return "I don't know."
        if checked_result.strip() != 'Y':
            query_result = ["I don't know"]
            logging.info("After two rounds, still no appropriate answer. Returning 'I don't know'.")

        ## Step Five: Given Query Results, generate the patient response
        logging.info("Step Five: Generating the patient response.")
        if query_result == ["I don't know"]:
            patient_response = "I don't know"
        else:
            rewrite_prompt = self.rewrite_response_prompt(conversation_history, doctor_query, query_result, patient_admission, personality_profile)
            if len(rewrite_prompt) > max_token:
                rewrite_prompt = rewrite_prompt[:max_token]
                logging.info(f"Rewrite prompt truncated to {max_token} characters.")
            patient_response = self.run_model(rewrite_prompt)
            logging.info(f"Patient response generated: {patient_response}")

        ## Step Six: Update the conversation history
        logging.info("Step Six: Updating the conversation history.")
        summarization_prompt = self.summarize_text_prompt(conversation_history, doctor_query, patient_response)
        if len(summarization_prompt) > max_token:
            summarization_prompt = summarization_prompt[:max_token]
            logging.info(f"Summarization prompt truncated to {max_token} characters.")
        summarization = self.run_model(summarization_prompt)
        logging.info(f"Conversation history updated: {summarization}")

        ## Update the conversation history based on the most recent interaction
        conversation_history = summarization
        logging.info(f"Conversation history: {conversation_history}")

        # Close the database connection
        db.close()
        logging.info("Database connection closed.")
        
        return patient_response, conversation_history
    
    def display_conversation(self, chat_placeholder):
        """Display the conversation in the chat placeholder."""
        with chat_placeholder.container():
            for idx, (doc_query, pat_response) in enumerate(st.session_state.conversation):
                timestamp = time.time()
                message(doc_query, is_user=True, key=f"doc_{idx}_{timestamp}", logo='https://raw.githubusercontent.com/huiziy/AIPatient_Image/master/doctor.png')
                message(pat_response, key=f"pat_{idx}_{timestamp}", logo='https://raw.githubusercontent.com/huiziy/AIPatient_Image/master/patient.png')

