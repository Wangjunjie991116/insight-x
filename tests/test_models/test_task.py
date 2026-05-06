"""Tests for task models."""

from datetime import datetime

from src.models.task import AnalysisTask, DatabaseConfig, TaskStatus


def test_database_config_connection_url():
    """Test database connection URL generation."""
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="test_user",
        password="test_pass",
    )
    assert config.connection_url == "postgresql://test_user:test_pass@localhost:5432/test_db"


def test_analysis_task_creation():
    """Test analysis task creation."""
    task = AnalysisTask(
        task_id="test-123",
        team_id="team-a",
        db_config=DatabaseConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
        ),
        business_doc="Test business document",
        business_goal="Test goal",
    )
    assert task.task_id == "test-123"
    assert task.status == TaskStatus.PENDING
    assert isinstance(task.created_at, datetime)


def test_task_status_transitions():
    """Test task status transitions."""
    task = AnalysisTask(
        task_id="test-123",
        team_id="team-a",
        db_config=DatabaseConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
        ),
        business_doc="Test",
        business_goal="Test",
    )

    task.mark_running()
    assert task.status == TaskStatus.RUNNING

    task.mark_completed()
    assert task.status == TaskStatus.COMPLETED
