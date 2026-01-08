"""
LangGraph workflow definition for invoice processing.

Creates a state machine that orchestrates extraction validation,
PO matching, risk assessment, and decision making.
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from .workflow_state import WorkflowState, WorkflowStatus
from .workflow_nodes import WorkflowNodes


logger = logging.getLogger(__name__)


def should_continue_after_validation(state: WorkflowState) -> Literal["continue", "error"]:
    """
    Determine whether to continue after extraction validation.
    
    Args:
        state: Current workflow state
        
    Returns:
        "continue" if validation succeeded, "error" otherwise
    """
    if state.get("extraction_completed") and not state.get("extraction_error"):
        return "continue"
    return "error"


def should_continue_after_parallel(state: WorkflowState) -> Literal["decide", "error"]:
    """
    Determine whether to proceed to decision after parallel processing.
    
    Args:
        state: Current workflow state
        
    Returns:
        "decide" if at least one step completed, "error" if both failed
    """
    matching_ok = state.get("matching_completed", False)
    risk_ok = state.get("risk_completed", False)
    
    # Continue to decision if at least one succeeded
    if matching_ok or risk_ok:
        return "decide"
    
    # If both failed, go to error handling
    return "error"


def create_workflow_graph(nodes: WorkflowNodes) -> StateGraph:
    """
    Create LangGraph workflow for invoice processing.
    
    The workflow follows this structure:
    1. Validate extraction
    2. Parallel execution: Match to PO + Assess risk
    3. Make decision
    4. Error handling (if needed)
    
    Args:
        nodes: WorkflowNodes instance with node functions
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating invoice processing workflow graph")
    
    # Create state graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("validate_extraction", nodes.validate_extraction)
    workflow.add_node("match_to_po", nodes.match_to_po)
    workflow.add_node("assess_risk", nodes.assess_risk)
    workflow.add_node("make_decision", nodes.make_decision)
    workflow.add_node("handle_error", nodes.handle_error)
    
    # Set entry point
    workflow.set_entry_point("validate_extraction")
    
    # Add conditional edge after validation
    workflow.add_conditional_edges(
        "validate_extraction",
        should_continue_after_validation,
        {
            "continue": "match_to_po",  # Continue to parallel processing
            "error": "handle_error",
        }
    )
    
    # Parallel execution: matching and risk assessment
    # Note: LangGraph executes nodes sequentially, but both steps are independent
    # and could be parallelized with custom execution logic
    workflow.add_edge("match_to_po", "assess_risk")
    
    # Conditional edge after parallel processing
    workflow.add_conditional_edges(
        "assess_risk",
        should_continue_after_parallel,
        {
            "decide": "make_decision",
            "error": "handle_error",
        }
    )
    
    # Terminal edges
    workflow.add_edge("make_decision", END)
    workflow.add_edge("handle_error", END)
    
    # Compile workflow
    compiled_workflow = workflow.compile()
    
    logger.info("Workflow graph created successfully")
    
    return compiled_workflow


# Workflow visualization for documentation
WORKFLOW_MERMAID = """
graph TD
    Start([Start]) --> Validate[Validate Extraction]
    Validate -->|Success| Match[Match to PO]
    Validate -->|Error| Error[Handle Error]
    
    Match --> Risk[Assess Risk]
    
    Risk -->|Success| Decide[Make Decision]
    Risk -->|Both Failed| Error
    
    Decide --> End([End])
    Error --> End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style Error fill:#FF6B6B
    style Decide fill:#4ECDC4
"""
