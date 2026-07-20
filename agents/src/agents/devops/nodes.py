"""
DevOps Agent — Node Functions

Flow:
  generate_deployment_plan → validate_plan 
  → [loop if invalid] → approve_deployment (Interrupt)
  → [loop if rejected] → execute_deployment → push_to_github → verify_health
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from agents.src.agents.devops.state import DevOpsState
from typing import Dict, Any
from agents.src.agents.devops.tools import (
    validate_iac_config,
    run_deployment,
    health_check_ping,
    push_github_actions
)

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
from langchain_groq import ChatGroq
import subprocess
import os
import requests
from pydantic import BaseModel, Field
from typing import List

class GeneratedFile(BaseModel):
    path: str = Field(description="The relative path to save the file to, e.g. docker-compose.yml")
    content: str = Field(description="The full raw code content of the file")

class CodeGenerationResponse(BaseModel):
    terminal_commands: List[str] = Field(default_factory=list, description="List of shell commands to execute")
    files: List[GeneratedFile] = Field(description="List of files to generate or update")

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_ROOT_DIR = Path(__file__).resolve().parents[4]

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

# ---------------------------------------------------------------------------
# 1. Generate Deployment Plan Node
# ---------------------------------------------------------------------------
def generate_deployment_plan_node(state: DevOpsState) -> dict:
    """
    Reads the final architecture design document.
    Generates Dockerfiles, docker-compose.yml, and CI/CD pipelines.
    """
    prompt_path = _PROMPTS_DIR / "devops.txt"
    prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    
    formatted = prompt.format(
        design=state.final_design_doc,
        feedback=state.deployment_feedback or "None.",
        linter=state.iac_validation_notes or "None."
    )
    
    structured_llm = _llm.with_structured_output(CodeGenerationResponse)
    generated_dump = []
    
    try:
        response = structured_llm.invoke(formatted)
        output_dir = _ROOT_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Terminal commands
        for cmd in response.terminal_commands:
            print(f"DevOps executing: {cmd}")
            try:
                res = subprocess.run(cmd, shell=True, cwd=str(output_dir), capture_output=True, text=True, check=True)
                generated_dump.append(f"Command '{cmd}' succeeded.\n{res.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"Command '{cmd}' failed: {e.stderr}")
                generated_dump.append(f"Command '{cmd}' failed.\n{e.stderr}")
        
        # Files
        for f in response.files:
            file_path = output_dir / f.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f.content, encoding="utf-8")
            print(f"DevOps wrote: output/{f.path}")
            generated_dump.append(f"File: output/{f.path}\n{f.content}")
            
    except Exception as e:
        print(f"Structured output failed: {e}")
        generated_dump.append(f"Error: {e}")
    
    return {
        "deployment_plan": "\n\n".join(generated_dump),
        "iteration_count": state.iteration_count + 1
    }

# ---------------------------------------------------------------------------
# GitHub Push Node (Deterministic — no LLM involved)
# ---------------------------------------------------------------------------
def push_to_github_node(state: DevOpsState) -> dict:
    """
    Creates a GitHub repo via the API and pushes the output/ directory.
    Only runs if github_repo_name is set in state.
    """
    from agents.src.shared.github import push_to_github
    res = push_to_github(state.github_repo_name, "DevOps Agent")
    return {"active_pr_number": res.get("pr_number", 0)}

# ---------------------------------------------------------------------------
# 2. Validate Plan Node
# ---------------------------------------------------------------------------
def validate_plan_node(state: DevOpsState) -> dict:
    """
    Runs the internal validation tool to lint the generated configurations.
    """
    notes = validate_iac_config.invoke({"iac_code": state.deployment_plan, "config_type": "auto"})
    return {"iac_validation_notes": notes}

# ---------------------------------------------------------------------------
# 3. Approve Deployment Node (Interrupt)
# ---------------------------------------------------------------------------
def approve_deployment_node(state: DevOpsState) -> dict:
    """
    Interrupts the graph to present the deployment scripts to the user before
    any physical infrastructure is provisioned or containers are started.
    """
    user_response = interrupt({
        "type": "deployment_approval",
        "plan": state.deployment_plan,
        "message": (
            "CRITICAL: The DevOps Agent is ready to deploy your application. "
            "Please review the deployment plan (Docker/Terraform scripts). "
            "Approve to proceed with actual deployment, or provide feedback."
        )
    })
    
    if not user_response or str(user_response).strip().lower() in ("approve", "yes", "ok", ""):
        return {"deployment_approved": True, "deployment_feedback": ""}
        
    return {"deployment_approved": False, "deployment_feedback": str(user_response)}

# ---------------------------------------------------------------------------
# 4. Execute Deployment Node
# ---------------------------------------------------------------------------
def execute_deployment_node(state: DevOpsState) -> dict:
    """
    Executes the deployment against the physical environment (Docker/Cloud)
    and pushes CI/CD pipelines to GitHub.
    """
    try:
        output_dir = _ROOT_DIR / "output"
        if (output_dir / "docker-compose.yml").exists():
            print("Running docker compose up -d --build...")
            res = subprocess.run("docker compose up -d --build", shell=True, cwd=str(output_dir), capture_output=True, text=True, check=True)
            logs = f"SUCCESS: Containers started.\n{res.stdout}"
        else:
            logs = "SUCCESS: Deployment mocked (no docker-compose.yml found)."
    except Exception as e:
        logs = f"Deployment failed: {e}"
        
    return {"deployment_logs": logs}

# ---------------------------------------------------------------------------
# 5. Verify Health Node
# ---------------------------------------------------------------------------
def verify_health_node(state: DevOpsState) -> dict:
    """
    Pings the live endpoint to verify the system is running.
    """
    try:
        from agents.src.agents.devops.tools import health_check_ping
        status = health_check_ping.invoke({"target_url": "http://localhost:8080/health"})
    except Exception as e:
        status = f"HEALTH_CHECK_FAILED: {e}"
        
    return {"health_check_status": status}

# ---------------------------------------------------------------------------
# Task Queue Management
# ---------------------------------------------------------------------------
def pop_task_node(state: DevOpsState) -> dict:
    tasks = list(state.workflow_tasks)
    if not tasks:
        return {"current_task": None}
    next_task = tasks.pop(0)
    return {"workflow_tasks": tasks, "current_task": next_task}

def mark_task_complete_node(state: DevOpsState) -> dict:
    return {"current_task": None}
