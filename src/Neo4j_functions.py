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
class Neo4jDatabase:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_random_patient_admission(self):
        with self.driver.session() as session:
            result = session.execute_read(self._fetch_random_patient_admission)
            return result

    ## Step One: randomly select patient from graph database
    @staticmethod
    def _fetch_random_patient_admission(tx):
        query = """
        MATCH (p:Patient)-[:HAS_ADMISSION]->(a:Admission)
        WITH p, a, rand() AS random
        ORDER BY random
        LIMIT 1
        RETURN p.SUBJECT_ID AS SubjectID, a.HADM_ID AS AdmissionID
        """
        result = tx.run(query)
        return result.single()

    ## Step Three: information extraction
    def execute_cypher_query(self, cypher_query):
        with self.driver.session() as session:
            result = session.execute_read(self._run_cypher_query, cypher_query)
            return result

    @staticmethod
    def _run_cypher_query(tx, cypher_query):
        result = tx.run(cypher_query)
        return [record[0] for record in result]