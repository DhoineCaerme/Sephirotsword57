import os
import json
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from schemas import InfrastructureIntent, LiveSystemState 
from tools import SafeBashTool

load_dotenv()


llm = tbd

def create_intent_extractor():
    """Creates and returns the Intent Extractor Agent."""
    return Agent(
        role='Infrastructure Intent Extractor',
        goal='Extract infrastructure requirements (ports, packages, services, env vars) from natural language documentation into strict JSON.',
        backstory='You are a senior DevOps engineer and parsing expert. You read operational documentation and accurately map out exactly what the server state needs to look like. You do not guess; if something is missing, you use "*".',
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
def create_os_prober():
    """Creates the OS Prober Agent."""
    return Agent(
        role='Linux OS Telemetry Prober',
        goal='Use safe Bash commands to probe the live system and verify if the requested infrastructure intent actually exists.',
        backstory='You are a master Linux Sysadmin. You know exactly which commands to run (e.g., ss -tuln, dpkg -l, systemctl status, printenv) to check the system state. You only run non-destructive, read-only commands.',
        verbose=True,
        allow_delegation=False,
        tools=[SafeBashTool()], # Give the agent our secure tool!
        llm=llm
    )

def create_probing_task(agent, intent_json):
    """Creates the task for the agent to probe the OS based on the intent."""
    return Task(
        description=f"""
        You have received the following desired Infrastructure Intent:
        {intent_json}
        
        Using the SafeBashTool, execute commands on this Linux machine to check if these specific ports, packages, services, and environment variables are active. 
        
        For example:
        - Use 'ss -tuln' or 'netstat' for ports.
        - Use 'dpkg -l | grep <pkg>' for packages.
        - Use 'systemctl is-active <service>' or 'docker ps' for services.
        
        Once you have gathered the telemetry, map your findings to the LiveSystemState JSON. Only list things that you verified are ACTUALLY running/installed.
        """,
        expected_output="A structured JSON object matching the LiveSystemState schema.",
        agent=agent,
        output_pydantic=LiveSystemState
    )

def create_extraction_task(agent, doc_snippet):
    """Creates the task for the agent to process a specific documentation snippet."""
    return Task(
        description=f"""
        Analyze the following DevOps documentation snippet:
        "{doc_snippet}"
        
        Extract the following:
        1. Required Ports
        2. Required Packages
        3. Required Services (systemd/Docker)
        4. Required Environment Variables (name and value)
        
        If the documentation is ambiguous, add a warning to the ambiguity_flags list.
        Think step-by-step before finalizing your output.
        """,
        expected_output="A structured JSON object matching the InfrastructureIntent schema.",
        agent=agent,
        output_pydantic=InfrastructureIntent # THIS IS THE MAGIC: It forces the AI to output your exact JSON schema!
    )

def run_extraction(doc_snippet):
    """Orchestrates the agent and task to process a snippet."""
    extractor_agent = create_intent_extractor()
    extraction_task = create_extraction_task(extractor_agent, doc_snippet)
    
    crew = Crew(
        agents=[extractor_agent],
        tasks=[extraction_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Run the crew
    result = crew.kickoff()
    return result


# --- TEST SCRIPT ---
if __name__ == "__main__":
    print("Starting Sephirotsword57 Intent Extractor...")
    
    test_doc = "For the frontend application to communicate with the backend API, ensure the node server is listening on port 8080."
    
    print(f"\n[DOCUMENTATION]: {test_doc}\n")
    print("Processing...")
    
    try:
        extracted_intent = run_extraction(test_doc)
        
        print("\n[EXTRACTION SUCCESSFUL]")
        print(json.dumps(extracted_intent.model_dump(), indent=2))
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        print("Note: If you got an authentication error, it means you need to add your API key to the .env file!")