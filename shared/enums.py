from enum import Enum

class AgentType(str, Enum):
    PLANNING = "planning"
    PRODUCT_MANAGER = "product_manager"
    ARCHITECT = "architect"
    TASK_BREAKDOWN = "task_breakdown"
    BACKEND_DEV = "backend_dev"
    FRONTEND_DEV = "frontend_dev"
    DATABASE = "database"
    QA = "qa"
    REVIEWER = "reviewer"
    DEVOPS = "devops"

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
