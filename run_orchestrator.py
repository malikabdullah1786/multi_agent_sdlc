import sys
import os
import uuid
from datetime import datetime

# Ensure the agents directory is in the python path
sys.path.append(os.path.abspath("."))

from agents.src.orchestrator.graph import orchestration_graph

def run_orchestrator():
    print("=" * 60)
    print("🤖 Welcome to the AI SDLC Orchestrator!")
    print("=" * 60)
    user_req = input("What would you like to build today? (Press Enter for default To-Do list app)\n> ")
    if not user_req.strip():
        user_req = "Create a fully functional to-do list web app with a React frontend and an Express/PostgreSQL backend."

    # Setup initial state
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Starting input (User Request)
    initial_state = {
        "user_req": user_req,
        "workflowId": thread_id,
        "projectId": f"ai-agent-project-{uuid.uuid4().hex[:6]}",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "prd": "",
        "project_name": "",
        "final_design_doc": "",
        "final_file_changes": [],
        "agent_logs": [],
        "human_interventions": [],
        "completed_task_titles": [],
        "workflow_tasks": [],
        "active_tasks": []
    }
    
    print(f"\n[Starting] SDLC Orchestrator [Thread: {thread_id}]")
    print("=" * 60)
    
    # Run the graph
    try:
        from langgraph.types import Command
        
        # Start initial graph execution
        current_input = initial_state
        
        while True:
            # Stream the execution to see what nodes are hit
            for event in orchestration_graph.stream(current_input, config=config):
                for node_name, state_update in event.items():
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] --- Node: {node_name} ---")
                    
                    if state_update:
                        # Print tasks and dispatcher routing
                        if "workflow_tasks" in state_update:
                            tasks = state_update["workflow_tasks"]
                            print(f"   ► Queue: {len(tasks)} tasks remaining.")
                            
                        if "current_task" in state_update and state_update["current_task"]:
                            task_title = state_update["current_task"].get("title", "Unknown Task")
                            print(f"   ► Executing Task: '{task_title}'")
                            
                        if "active_role" in state_update and state_update["active_role"]:
                            role = state_update["active_role"]
                            active = len(state_update.get("active_tasks", []))
                            print(f"   ► Dispatcher routed to: [{role}] with {active} task(s).")
                            
                        # Print dynamically added tasks (Feedback loops)
                        if "new_workflow_tasks" in state_update and state_update["new_workflow_tasks"]:
                            print(f"   ► [DYNAMIC FEEDBACK]: {len(state_update['new_workflow_tasks'])} new tasks spawned!")
                            for t in state_update["new_workflow_tasks"]:
                                print(f"      - {t.get('title')}")
                                
                        # Print core document outputs
                        if "prd" in state_update and state_update["prd"]:
                            print(f"   ► PRD Generated! ({len(state_update['prd'])} chars)")
                        if "final_design_doc" in state_update and state_update["final_design_doc"]:
                            print(f"   ► Architecture Design Doc Generated! ({len(state_update['final_design_doc'])} chars)")
                            
                        # Print Code Gen statuses
                        if "generated_ui_code" in state_update and state_update["generated_ui_code"]:
                            print(f"   ► Frontend Code Written: {len(state_update['generated_ui_code'])} files/commands.")
                        if "current_code_draft" in state_update and state_update["current_code_draft"]:
                            print(f"   ► Backend Code Written ({len(state_update['current_code_draft'])} chars).")
                            
                        # Print Tests & QA
                        if "test_failures" in state_update and state_update["test_failures"]:
                            print(f"   ► Test Results: {len(state_update['test_failures'])} chars.")
                        if "test_run_output" in state_update and state_update["test_run_output"]:
                            print(f"   ► QA Test Execution Completed.")
                        if "all_tests_passed" in state_update:
                            passed = state_update["all_tests_passed"]
                            print(f"   ► All Tests Passed: {passed}")
                            
                        # Print Reviewer and Security
                        if "code_review_approved" in state_update:
                            print(f"   ► Code Review Approved: {state_update['code_review_approved']}")
                        if "security_approved" in state_update:
                            print(f"   ► Security Approved: {state_update['security_approved']}")

            # Check if execution finished or hit an interrupt
            state = orchestration_graph.get_state(config)
            has_interrupts = False
            interrupts = []
            if state.tasks:
                for task in state.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        has_interrupts = True
                        interrupts.extend(task.interrupts)

            if not state.next and not has_interrupts:
                # Graph fully finished
                print("\n[Finished] Orchestrator run completed successfully.")
                break
                
            # We hit an interrupt! Find the payload
            if interrupts:
                payload = interrupts[0].value
                print("\n" + "=" * 60)
                print("[HUMAN APPROVAL REQUIRED]")
                print("=" * 60)
                
                draft_content = ""
                if isinstance(payload, dict):
                    if "message" in payload:
                        print(f"Message: {payload['message']}")
                    if "questions" in payload and payload["questions"]:
                        print("\nQuestions:")
                        for q in payload["questions"]:
                            print(f"- {q}")
                    if "section" in payload:
                        print(f"Section to Review: {payload['section']}")
                    if "draft" in payload:
                        draft_content = payload["draft"]
                    elif "content" in payload:
                        draft_content = payload["content"]
                else:
                    print(f"Agent requires feedback: {payload}")
                    if isinstance(payload, str):
                        draft_content = payload
                
                if draft_content:
                    try:
                        with open("current_draft_review.md", "w", encoding="utf-8") as f:
                            f.write(draft_content)
                        print("👉 [Action Required]: The draft content has been saved to 'current_draft_review.md' in your workspace root.")
                        print("   Please open that file in your editor to inspect it.")
                    except Exception as e:
                        print(f"Failed to write draft to file: {e}")
                        
                user_feedback = input("\nYour response (press Enter to approve, or type specific feedback): ")
                print("Resuming graph execution...")
                
                # Resume execution with the user's feedback
                current_input = Command(resume=user_feedback)
            else:
                # If there are pending nodes but no explicit interrupt payload, 
                # just resume with None (though this is rare unless manually paused).
                current_input = None
    except Exception as e:
        print(f"\n[Error] Orchestrator Execution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_orchestrator()
