from .data_validator import DataConstraintValidator
from .completion_checker import CodeVerifiedCompletionChecker
from .permission_guard import PermissionGuard
from .human_handoff import HumanHandoffController
from schema import HarnessCheckResult

class AgentHarness:
    def __init__(self):
        self.validator = DataConstraintValidator()
        self.completion_checker = CodeVerifiedCompletionChecker()
        self.permission_guard = PermissionGuard()
        self.handoff_controller = HumanHandoffController()

    def check_tool_call(self, tool_name: str, kwargs: dict, user_approval_token: str = None) -> HarnessCheckResult:
        return self.permission_guard.check_tool_permission(tool_name, kwargs, user_approval_token)

    def verify_completion(self, origin: str, destination: str, departure_date: str, num_passengers: int, max_budget: float = None, expected_pnr: str = None) -> HarnessCheckResult:
        return self.completion_checker.verify_booking_completed(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            num_passengers=num_passengers,
            max_budget=max_budget,
            expected_pnr=expected_pnr
        )

    def check_handoff(self, tool_output: str, step_count: int, max_steps: int = 10) -> HarnessCheckResult:
        return self.handoff_controller.evaluate_handoff_needed(tool_output, step_count, max_steps)
