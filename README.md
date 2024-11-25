# AIPatient: Large Language Model Powered Simulated Patient for Medical Education

[![Code License](https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg)](https://github.com/huiziy/AIPatient/blob/main/LICENSE)

<h2 align="center"><strong>Realistic</strong> &mdash; <strong>Diverse</strong> &mdash; <strong>Factual</strong> &mdash; <strong>Scalable</strong></h2>

<img align="center" width="854" alt="Overview" src="fig/AIPatient_Fig1.png">
<p align="center"><strong>Figure 1:</strong> AIPatient Structure</p>

**Motivation:** Traditional medical education faces many challenges, including limited access to diverse clinical experiences, inconsistency in medical training, and high costs and limitated standardization in recruiting volunteers to serve as simulated patients. Integrating new technologies such as Large Language Models (LLM) can enhance the learning experience and improve training outcomes. 

**Overview:** In this project, we developed **AIPatient**, an LLM powered simulated patient based on Electronic Health Records (EHR) data. Leveraging the MIMIC III dataset, which includes over 46k<sup>[1](#myfootnote1)</sup> patients, we began by extracting relevant medical entities and their relationships to construct a comprehensive knowledge graph (KG). Next, we designed a multi-agent system and proposed the **Reasoning RAG** framework to accurately represent the information within the KG, ensuring minimal hallucination and high factual accuracy. By incorporating personalities, AIPatient can mimic real-life interactions, responding to questions and presenting symptoms in a manner similar to actual patients. In future iterations, we aim to incorporate evaluator agent to provide feedback on user performance, potentially enhancing medical training and ultimately improving patient care outcomes. 

<a name="myfootnote1">1</a>: For the current iteration, AIPatient contains 100 unique cases. We plan to scale the patient pool in the future. 

## LLM Agent Interaction

<img align="center" width="854" alt="AgentOverview" src="fig/AIPatient_Fig2.png">
<p align="center"><strong>Figure 2:</strong> AIPatient Multi-Agent</p>

<strong>Figure 2</strong> presents the multi-agent system, designed with Reasoning RAG framework (Retrieval, Reasoning, Generation). Each rounds, agents interact to ensure accurate data retrieval and realistic generation. The system is also memory-perserving to ensure multi-round capabilities. 

## From EHR to Knowledge Graph

<img align="center" width="854" alt="EHRKG" src="fig/AIPatient_Fig3a.png">
<p align="center"><strong>Figure 3:</strong> Knowledge Graph Construction with Electronic Health Records</p>

<strong>Figure 3</strong> provides an example of KG (right) constructed using EHR data (left). In the current KG, we focus on 12 node types (e.g. Admission, Symptom) and 11 relationships (e.g. HAS_SYMPTOM). The rich and diverse notes data in MIMIC III presents opportunities for mining additional medical entities and relationships. 

## Case Study

<img align="center" width="854" alt="AgentsCase" src="fig/AIPatient_Fig3b.png">
<p align="center"><strong>Figure 4:</strong> AIPatient Interaction Example (single round) </p>

In <strong>Figure 4</strong>, we present one round of user-AIPatient interaction. Beginning with user's natural language query input, the backend of AIPatient engages various agents and update the session state accordingly. Finally, the Simulated Patient answers the user's query using natural language. 

## Future Directions and Implications
We are currently working on:
- Onboarding 46,000+ patients’ EHR to our AIPatient platform
- Evaluating model and workflow capability 
- Enriching the knowledge graph with additional medical entities and relationships
- Optimizing for computation efficiency 

AIPatient has implications:
- Beyond traditional medical settings, systems similar to AIPatient could significantly assisting EMS training by providing realistic, scenario-based training for paramedics and emergency responders, dealing with diverse medical emergencies like trauma assessments or cardiac events. Additionally, it could be used in remote or underserved areas to train healthcare workers on complex case management without the need for physical simulation centers.
- In educational contexts beyond medical training, systems similar to AIPatient could be adapted for language development, helping students practice terminology and communication skills in different languages. Furthermore, it could be utilized in fields like psychology or social work education, allowing students to engage in simulated interactions with people in need who exhibiting various mental health conditions or social scenarios, enhancing their diagnostic and interpersonal skills.

## QuickStart
### Install Environment
```
conda create --name aipatient python=3.9
conda activate aipatient

git clone [https://github.com/huiziy/AIPatient2024.git]

cd AIPatient2024
pip install -r requirements.txt
```

### Set up API keys
Currently, AIPatient supports Claude 3.5 Sonnet. To use Claude 3.5 Sonnet on Amazon Bedrock, follow [this guide](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock) to install AWS CLI, set up AWS IAM account and request access for Claude 3.5 Sonnet. 

After obtaining "Access key ID" and "Secret access key". Navigate to ```secrets.txt``` file in this repo and add your keys after "Access_key_ID" and "Secret_access_key" respectively. 

### Run AIPatient Interface
The AIPatient interface is designed with [streamlit](https://streamlit.io). To run the app locally:
```
cd src
streamlit run AIPatient_Interface.py
```

## License
The source code of AIPatient is licensed under [Apache 2.0](https://github.com/tatsu-lab/stanford_alpaca/blob/main/LICENSE). The intended purpose is solely for research use.

## Disclaimer
AIPatient is powered by Anthropic's Claude 3.5 Sonnet via Amazon Bedrock to comform with the [Responsible Data Use Agreement](https://physionet.org/news/post/gpt-responsible-use). We confirm the data is not shared with third parties, including sending it through APIs or using it in online platforms.

This repo contains code for agents and QA Interface; some data cleaning and knowledge graph creation code are omitted and will be made public after paper publication. 

