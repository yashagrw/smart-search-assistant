"""
Unit and Integration Tests for Database and RAG Services.
Validates SQLite execution, SQL injection defenses, and Two-Stage Re-ranking retrieval.
"""

import os
import sys

# Ensure project root is in sys.path for test runners
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.project_service import project_service_v1
from src.services.order_service import order_service_v1
from src.services.rag_service import query_knowledge_base, compute_rerank_score

def test_project_service_deterministic_record():
    """Verify that Project P185602 exists and returns 'open' status."""
    query = "SELECT name, status FROM projects WHERE name = 'Project P185602'"
    result = project_service_v1(query)
    
    assert isinstance(result, list), "Expected result to be a list of rows"
    assert len(result) > 0, "Project P185602 must exist in the database"
    assert result[0][0] == "Project P185602"
    assert result[0][1] == "open"

def test_project_service_disallows_non_select():
    """Verify that destructive SQL statements (DROP/INSERT/DELETE) are blocked."""
    destructive_query = "DELETE FROM projects WHERE id = 1"
    result = project_service_v1(destructive_query)
    
    assert isinstance(result, dict), "Non-SELECT queries must return an error dictionary"
    assert "error" in result

def test_order_service_deterministic_record():
    """Verify that Order END1234567 exists with 'order_processing' displayStatus."""
    query = "SELECT fileNum, displayStatus FROM orders WHERE fileNum = 'END1234567'"
    result = order_service_v1(query)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0][0] == "END1234567"
    assert result[0][1] == "order_processing"

def test_compute_rerank_score_math():
    """Verify the deterministic cross-scoring re-ranker algorithm."""
    query = "daily meal allowance travel"
    doc = "Employees receive a Daily Meal Per Diem allowance capped at $85 during travel."
    metadata = {"department": "FINANCE", "section": "DAILY MEAL ALLOWANCE"}
    
    score = compute_rerank_score(query, doc, metadata)
    assert score > 0.8, "Exact matching terms and matching metadata must score high"

def test_two_stage_rag_finance_retrieval():
    """Integration test verifying Re-ranked RAG fetches Finance policy correctly."""
    query = "What is the daily meal limit during business travel?"
    result = query_knowledge_base(query)
    
    assert "Dept: FINANCE" in result, "Result must contain the Finance department tag"
    assert "$85" in result, "Result must contain the exact $85 per diem amount"