from schema import HarnessCheckResult
from typing import Dict, Any, Optional


class HumanHandoffController:
    
    @staticmethod
    def evaluate_handoff_needed(
        tool_output: str,
        step_count: int,
        max_steps: int = 10
    ) -> HarnessCheckResult:

        if step_count >= max_steps:
            return HarnessCheckResult(
                passed=False,
                check_type="HandOff",
                details=f"HAND-OFF TRIGGERED: Agent vượt quá số bước tối đa ({max_steps} bước). Cần bàn giao cho Nhân viên hỗ trợ.",
                action_required="HANDOFF_TO_HUMAN"
            )

        if "Không tìm thấy chuyến bay" in tool_output and "ngân sách" in tool_output:
            return HarnessCheckResult(
                passed=False,
                check_type="HandOff",
                details="HAND-OFF TRIGGERED: Không tìm thấy vé máy bay trong phạm vi ngân sách. Bàn giao để người dùng điều chỉnh ngân sách hoặc chọn ngày khác.",
                action_required="ASK_USER_FEEDBACK"
            )

        return HarnessCheckResult(
            passed=True,
            check_type="HandOff",
            details="Chưa cần bàn giao, tiếp tục xử lý tự động."
        )
