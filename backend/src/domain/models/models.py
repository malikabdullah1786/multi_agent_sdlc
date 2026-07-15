from sqlalchemy import Column,Integer,String,DateTime,Boolean,ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()

class ProjectSchema(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    current_status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    git_url = Column(String, nullable=False)
    path = Column(String,nullable=False)


class WorkflowSchema(Base):
    __tablename__ = "workflows"
    id = Column(Integer,primary_key=True)
    project_id = Column(Integer,ForeignKey("projects.id"),nullable=False)
    current_state = Column(String,nullable=False)
    created_at = Column(DateTime,nullable=False)
    updated_at = Column(DateTime,nullable=False)
    target_branch = Column(String,nullable=False)
    source_branch = Column(String,nullable=False)
    summary = Column(String,nullable=False)
    status = Column(String,nullable=False)
    next_agent = Column(String,nullable=False)


class HumanApprovalSchema(Base):
    __tablename__ = "human_approval"
    id = Column(Integer,primary_key=True)
    workflow_id = Column(Integer,ForeignKey("workflows.id"),nullable=False)
    created_at = Column(DateTime,nullable=False)
    updated_at = Column(DateTime,nullable=False)
    status = Column(String,nullable=False)
    requesting_agent_id = Column(String,nullable=False)
    request_details = Column(String,nullable=False)
    payload = Column(String,nullable=False)
    feed_back = Column(String,nullable=True)

class AgentLogSchema(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer,primary_key=True)
    workflow_id = Column(Integer,ForeignKey("workflows.id"),nullable=False)
    created_at = Column(DateTime,nullable=False)
    updated_at = Column(DateTime,nullable=False)
    status = Column(String,nullable=False)
    requesting_agent_id = Column(String,nullable=False)
    request_details = Column(String,nullable=False)
    payload = Column(String,nullable=False)
    response = Column(String,nullable=False)

class TaskSchema(Base):
    __tablename__ = "tasks"
    id = Column(Integer,primary_key=True)
    workflow_id = Column(Integer,ForeignKey("workflows.id"),nullable=False)
    created_at = Column(DateTime,nullable=False)
    updated_at = Column(DateTime,nullable=False)
    status = Column(String,nullable=False)
    requesting_agent_id = Column(String,nullable=False)
    request_details = Column(String,nullable=False)
    payload = Column(String,nullable=False)
    response = Column(String,nullable=False)
    