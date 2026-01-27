#!/usr/bin/env python3
"""
Interactive testing harness for SQL tool validation.

Usage:
    python scripts/test_sql_tool.py "How many orders were placed last week?"
    python scripts/test_sql_tool.py --interactive
    python scripts/test_sql_tool.py --test-suite
"""

import argparse
import json
import logging
from typing import Any
from uuid import uuid4

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SQLToolTester:
    """Interactive tester for the SQL tool."""

    def __init__(self):
        """Initialize the tester."""
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> dict[str, dict[str, Any]]:
        """Load predefined test cases."""
        return {
            "simple_count": {
                "description": "Simple aggregation (count)",
                "question": "How many customers do we have?",
                "client_id": "test-tenant-123",
                "role": "analyst",
                "expected_success": True,
                "expected_columns": ["count"],
            },
            "with_filter": {
                "description": "Query with date filter",
                "question": "How many orders in the last 7 days?",
                "client_id": "test-tenant-123",
                "role": "analyst",
                "optional_constraints": {"date_range": "last_7_days"},
                "expected_success": True,
                "expected_columns": ["count"],
            },
            "join_query": {
                "description": "Query with JOIN",
                "question": "Show me top 5 customers by revenue",
                "client_id": "test-tenant-123",
                "role": "analyst",
                "expected_success": True,
                "expected_columns": ["name", "revenue"],
            },
            "validation_failure": {
                "description": "Query that should fail validation",
                "question": "Show me all data from the internal audit table",
                "client_id": "test-tenant-123",
                "role": "viewer",
                "expected_success": False,
                "expected_error_code": "validation_failed",
            },
            "viewer_role_limit": {
                "description": "Viewer role with restricted access",
                "question": "List all transactions",
                "client_id": "test-tenant-123",
                "role": "viewer",
                "expected_success": False,
                "expected_error_code": "validation_failed",
            },
        }

    def run_single_test(
        self,
        question: str,
        client_id: str,
        role: str,
        optional_constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run a single test invocation.

        Args:
            question: Natural language question
            client_id: Client identifier
            role: User role
            optional_constraints: Optional query constraints

        Returns:
            Result dictionary with execution details
        """
        from vizu_tool_registry.tools.sql_tool import QueryDatabaseTextToSQL, SQLToolInput

        logger.info(f"Running test: question='{question}', role={role}")

        tool = QueryDatabaseTextToSQL()
        input_params = SQLToolInput(
            question=question,
            client_id=client_id,
            role=role,
            optional_constraints=optional_constraints,
        )

        try:
            result = tool.invoke(input_params)
            output = result.to_dict()
            output["test_duration_ms"] = 0  # Would be filled in by caller
            return {
                "status": "success",
                "output": output,
                "telemetry_id": output.get("telemetry_id"),
            }
        except Exception as e:
            logger.exception(f"Test execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "telemetry_id": str(uuid4()),
            }

    def validate_result(
        self,
        result: dict[str, Any],
        expected_success: bool,
        expected_error_code: str | None = None,
        expected_columns: list | None = None,
    ) -> dict[str, Any]:
        """
        Validate a result against expectations.

        Args:
            result: Result from run_single_test
            expected_success: Whether query should succeed
            expected_error_code: Expected error code if failure expected
            expected_columns: Expected column names if success expected

        Returns:
            Validation result dict
        """
        if result["status"] == "error":
            return {
                "passed": False,
                "reason": f"Test execution error: {result['error']}",
            }

        output = result["output"]
        query_success = output["success"]

        # Check success/failure
        if query_success != expected_success:
            return {
                "passed": False,
                "reason": (
                    f"Expected {'success' if expected_success else 'failure'}, "
                    f"got {'success' if query_success else 'failure'}"
                ),
            }

        # Check error code if failure expected
        if not expected_success:
            if expected_error_code:
                actual_error_code = output.get("error", {}).get("code")
                if actual_error_code != expected_error_code:
                    return {
                        "passed": False,
                        "reason": f"Expected error code '{expected_error_code}', got '{actual_error_code}'",
                    }

        # Check columns if success expected
        if expected_success and expected_columns:
            actual_columns = [col["name"] for col in output.get("columns", [])]
            missing = set(expected_columns) - set(actual_columns)
            if missing:
                return {
                    "passed": False,
                    "reason": f"Missing columns: {missing}. Got: {actual_columns}",
                }

        return {"passed": True, "reason": "All checks passed"}

    def run_test_suite(self) -> dict[str, Any]:
        """
        Run the full test suite.

        Returns:
            Summary of all test results
        """
        results = {
            "total": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "tests": {},
        }

        for test_name, test_config in self.test_cases.items():
            logger.info(f"Running test: {test_name} - {test_config['description']}")

            result = self.run_single_test(
                question=test_config["question"],
                client_id=test_config["client_id"],
                role=test_config["role"],
                optional_constraints=test_config.get("optional_constraints"),
            )

            validation = self.validate_result(
                result,
                expected_success=test_config.get("expected_success", True),
                expected_error_code=test_config.get("expected_error_code"),
                expected_columns=test_config.get("expected_columns"),
            )

            test_result = {
                "description": test_config["description"],
                "passed": validation["passed"],
                "reason": validation["reason"],
                "telemetry_id": result.get("telemetry_id"),
            }

            if validation["passed"]:
                results["passed"] += 1
                logger.info(f"✓ {test_name}: PASSED")
            else:
                results["failed"] += 1
                logger.warning(f"✗ {test_name}: FAILED - {validation['reason']}")

            results["tests"][test_name] = test_result

        return results

    def interactive_mode(self):
        """Run in interactive mode."""
        print("\n=== SQL Tool Interactive Tester ===\n")
        print("Commands:")
        print("  q <question>     - Run a question")
        print("  suite            - Run full test suite")
        print("  help             - Show available test cases")
        print("  exit             - Exit\n")

        while True:
            try:
                user_input = input("test> ").strip()

                if not user_input:
                    continue

                if user_input == "exit":
                    print("Goodbye!")
                    break

                if user_input == "suite":
                    print("\nRunning full test suite...")
                    results = self.run_test_suite()
                    print(json.dumps(results, indent=2))
                    continue

                if user_input == "help":
                    print("\nAvailable test cases:")
                    for name, config in self.test_cases.items():
                        print(f"  {name}: {config['description']}")
                    print()
                    continue

                if user_input.startswith("q "):
                    question = user_input[2:].strip()
                    result = self.run_single_test(
                        question=question,
                        client_id="test-tenant-123",
                        role="analyst",
                    )
                    print("\nResult:")
                    print(json.dumps(result, indent=2))
                    print()
                    continue

                print("Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.exception(f"Error: {e}")
                print(f"Error: {e}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive testing harness for SQL tool"
    )
    parser.add_argument("question", nargs="?", help="Question to test")
    parser.add_argument(
        "--role",
        default="analyst",
        choices=["viewer", "analyst", "admin"],
        help="User role",
    )
    parser.add_argument(
        "--client-id",
        dest="client_id",
        default="test-tenant-123",
        help="Client identifier",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--test-suite",
        action="store_true",
        help="Run full test suite",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    tester = SQLToolTester()

    if args.interactive:
        tester.interactive_mode()
    elif args.test_suite:
        results = tester.run_test_suite()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n=== Test Suite Results ===")
            print(f"Total: {results['total']}")
            print(f"Passed: {results['passed']}")
            print(f"Failed: {results['failed']}")
            for name, test_result in results["tests"].items():
                status = "✓" if test_result["passed"] else "✗"
                print(f"{status} {name}: {test_result['reason']}")
    elif args.question:
        result = tester.run_single_test(
            question=args.question,
            client_id=args.client_id,
            role=args.role,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            output = result.get("output", {})
            print(f"\nQuestion: {args.question}")
            print(f"Role: {args.role}")
            print(f"Success: {output.get('success')}")
            if output.get("success"):
                print(f"Rows: {len(output.get('rows', []))}")
                print(f"Columns: {[c['name'] for c in output.get('columns', [])]}")
            else:
                error = output.get("error", {})
                print(f"Error: {error.get('code')}")
                print(f"Message: {error.get('message')}")
                print(f"Suggestion: {error.get('suggestion')}")
            print(f"Telemetry ID: {output.get('telemetry_id')}")
            print(f"Execution Time: {output.get('execution_time_ms')}ms\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
