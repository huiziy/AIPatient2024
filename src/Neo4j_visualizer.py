import streamlit as st
from py2neo import Graph, Node as Py2neoNode, Relationship as Py2neoRelationship
from streamlit_agraph import agraph, Node, Edge, Config

class Neo4jGraphVisualizer:
    def __init__(self, uri, user, password):
        self.graph = Graph(uri, auth=(user, password))

    def fetch_admissions(self, hadm_id):
        query = f"""
        MATCH (p:Patient)-[r1:HAS_ADMISSION]->(a:Admission {{HADM_ID: {hadm_id}}})
        RETURN p, r1, a
        """
        return self.graph.run(query)

    def fetch_histories(self, hadm_id):
        query = f"""
        MATCH (p:Patient)-[r2:HAS_MEDICAL_HISTORY]->(h:History)
        WHERE EXISTS((p)-[:HAS_ADMISSION]->(:Admission {{HADM_ID: {hadm_id}}}))
        RETURN p, r2, h
        """
        return self.graph.run(query)

    def fetch_symptoms(self, hadm_id):
        query = f"""
        MATCH (a:Admission {{HADM_ID: {hadm_id}}})-[r3:HAS_SYMPTOM]->(s:Symptom)
        RETURN a, r3, s
        """
        return self.graph.run(query)

    def fetch_durations(self, hadm_id):
        query = f"""
        MATCH (s:Symptom)-[r4:HAS_DURATION]->(d:Duration)
        WHERE EXISTS((:Admission {{HADM_ID: {hadm_id}}})-[:HAS_SYMPTOM]->(s))
        RETURN s, r4, d
        """
        return self.graph.run(query)

    def fetch_frequencies(self, hadm_id):
        query = f"""
        MATCH (s:Symptom)-[r5:HAS_FREQUENCY]->(f:Frequency)
        WHERE EXISTS((:Admission {{HADM_ID: {hadm_id}}})-[:HAS_SYMPTOM]->(s))
        RETURN s, r5, f
        """
        return self.graph.run(query)

    def fetch_intensities(self, hadm_id):
        query = f"""
        MATCH (s:Symptom)-[r6:HAS_INTENSITY]->(i:Intensity)
        WHERE EXISTS((:Admission {{HADM_ID: {hadm_id}}})-[:HAS_SYMPTOM]->(s))
        RETURN s, r6, i
        """
        return self.graph.run(query)

    def fetch_vitals(self, hadm_id):
        query = f"""
        MATCH (a:Admission {{HADM_ID: {hadm_id}}})-[r7:HAS_VITAL]->(v:Vital)
        RETURN a, r7, v
        """
        return self.graph.run(query)

    def fetch_no_symptoms(self, hadm_id):
        query = f"""
        MATCH (a:Admission {{HADM_ID: {hadm_id}}})-[r8:HAS_NOSYMPTOM]->(ns:Symptom)
        RETURN a, r8, ns
        """
        return self.graph.run(query)
    
    def fetch_allergies(self, hadm_id):
        query = f"""
        MATCH (a:Admission {{HADM_ID: {hadm_id}}})-[r:HAS_ALLERGY]->(al:Allergy)
        MATCH (p:Patient)-[:HAS_ADMISSION]->(a)
        RETURN p, a, r, al
        """
        return self.graph.run(query).data()

    def fetch_social_history(self, hadm_id):
        query = f"""
        MATCH (a:Admission {{HADM_ID: {hadm_id}}})-[r:HAS_SOCIAL_HISTORY]->(sh:SocialHistory)
        MATCH (p:Patient)-[:HAS_ADMISSION]->(a)
        RETURN p, a, r, sh
        """
        return self.graph.run(query).data()

    def fetch_family_history(self, hadm_id):
        query = f"""
        MATCH (p:Patient)-[r:HAS_ADMISSION]->(a:Admission {{HADM_ID: {hadm_id}}})
        MATCH (p)-[r2:HAS_FAMILY_MEMBER]->(fm:FamilyMember)
        OPTIONAL MATCH (fm)-[r3:HAS_MEDICAL_HISTORY]->(fmh:FamilyMedicalHistory)
        WHERE EXISTS((p)-[:HAS_ADMISSION]->(a))
        RETURN p, r, a, r2, fm, r3, fmh
        """
        return self.graph.run(query).data()

    def fetch_data(self, hadm_id):
        results = []
        results.extend(self.fetch_admissions(hadm_id))
        results.extend(self.fetch_histories(hadm_id))
        results.extend(self.fetch_symptoms(hadm_id))
        results.extend(self.fetch_durations(hadm_id))
        results.extend(self.fetch_frequencies(hadm_id))
        results.extend(self.fetch_intensities(hadm_id))
        results.extend(self.fetch_vitals(hadm_id))
        results.extend(self.fetch_no_symptoms(hadm_id))
        results.extend(self.fetch_allergies(hadm_id))
        results.extend(self.fetch_social_history(hadm_id))
        results.extend(self.fetch_family_history(hadm_id))
        return results

    def get_node_color(self, label):
        color_map = {
            'Patient': 'green',
            'Admission': 'red',
            'Symptom': 'blue',
            'Vital': 'orange',
            'Intensity': 'purple',
            'Duration': 'purple',
            'Frequency': 'purple',
            'MedicalHistory': 'gray',
            'Allergy': 'yellow',
            'SocialHistory': 'brown',
            'FamilyMember': 'cyan',
            'FamilyMedicalHistory': 'pink'
        }
        return color_map.get(label, 'grey')

    def create_nodes_edges(self, results):
        nodes = []
        edges = []
        node_set = set()  # To avoid duplicate nodes

        for record in results:
            for key, value in record.items():
                if isinstance(value, Py2neoNode):
                    node_id = str(value.identity)
                    if node_id not in node_set:
                        label = list(value.labels)[0]
                        color = self.get_node_color(label)
                        props = {k: str(v) for k, v in dict(value).items()}  # Ensure all properties are strings
                        description = "\n".join([f"{k}: {v}" for k, v in props.items()])
                        node = Node(id=node_id, label=label, size=15, title=description, color=color, **props)  # Explicit node size and title
                        nodes.append(node)
                        node_set.add(node_id)
                elif isinstance(value, Py2neoRelationship):
                    source_id = str(value.start_node.identity)
                    target_id = str(value.end_node.identity)
                    edge = Edge(source=source_id, target=target_id)
                    edges.append(edge)

        return nodes, edges

    def visualize_graph(self, nodes, edges):
        config = Config(
            width=1000, height=1000, directed=True, 
            nodeHighlightBehavior=True, highlightColor="#F7A7A6", 
            collapsible=True, 
            node={'labelProperty': 'label', 'size': 30},  # Global node size adjustment
            edge={'font': {'size': 20}}  # Adjust edge label font size here
        )
        return agraph(nodes=nodes, edges=edges, config=config)