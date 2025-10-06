"""Health check service for infrastructure validation."""

import asyncio
from typing import Any

from pydantic import BaseModel
from sqlalchemy import text

from ml_agents_v2.infrastructure.database.session_manager import DatabaseSessionManager
from ml_agents_v2.infrastructure.logging_setup import get_logger
from ml_agents_v2.infrastructure.providers import OpenRouterClient


class HealthStatus(BaseModel):
    """Health check status model.

    Represents the overall health status of the system and its components.
    """

    status: str  # "healthy", "degraded", "unhealthy"
    checks: dict[str, Any]


class HealthChecker:
    """Performs comprehensive health checks on infrastructure components.

    Validates connectivity and functionality of database, OpenRouter API,
    and other critical system components.
    """

    def __init__(
        self,
        database_session_manager: DatabaseSessionManager,
        openrouter_client: OpenRouterClient,
    ):
        """Initialize health checker with infrastructure components.

        Args:
            database_session_manager: Database session manager
            openrouter_client: OpenRouter API client
        """
        self.database_session_manager = database_session_manager
        self.openrouter_client = openrouter_client
        self.logger = get_logger(__name__)

    def check_health(self) -> HealthStatus:
        """Perform comprehensive health check.

        Returns:
            HealthStatus with overall status and component details
        """
        checks = {}

        # Database connectivity check
        checks["database"] = self._check_database()

        # OpenRouter connectivity check
        checks["openrouter"] = self._check_openrouter()

        # Determine overall status
        overall_status = self._determine_overall_status(checks)

        return HealthStatus(status=overall_status, checks=checks)

    def _check_database(self) -> dict[str, Any]:
        """Check database connectivity and basic functionality.

        Returns:
            Dictionary with database health status and details
        """
        try:
            with self.database_session_manager.get_session() as session:
                # Simple query to test connectivity
                result = session.execute(text("SELECT 1"))
                result.scalar()

            return {"status": "healthy", "message": "Database connection successful"}

        except Exception as e:
            self.logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": "Database connection failed",
                "error": str(e),
            }

    def _check_openrouter(self) -> dict[str, Any]:
        """Check OpenRouter API connectivity and authentication.

        Returns:
            Dictionary with OpenRouter health status and details
        """
        try:
            # Use the health_check method from the OpenRouter client (now async)
            response = asyncio.run(self.openrouter_client.health_check())

            # Extract useful information from the response
            status_info = {
                "status": "healthy",
                "message": "OpenRouter API connection successful",
            }

            # Add credit information if available
            if "credit_left" in response:
                status_info["credit_left"] = response["credit_left"]

            # Add usage information if available
            if "usage" in response:
                status_info["usage"] = response["usage"]

            return status_info

        except Exception as e:
            self.logger.error("OpenRouter health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": "OpenRouter API connection failed",
                "error": str(e),
            }

    def _determine_overall_status(self, checks: dict[str, Any]) -> str:
        """Determine overall system health status.

        Args:
            checks: Dictionary of component health check results

        Returns:
            Overall status: "healthy", "degraded", or "unhealthy"
        """
        unhealthy_count = 0
        total_checks = len(checks)

        for check in checks.values():
            if check["status"] == "unhealthy":
                unhealthy_count += 1

        # If all components are healthy
        if unhealthy_count == 0:
            return "healthy"

        # If all components are unhealthy
        if unhealthy_count == total_checks:
            return "unhealthy"

        # If some components are unhealthy (mixed state)
        return "degraded"
