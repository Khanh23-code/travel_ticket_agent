from schema import HarnessCheckResult, PermissionLevel
from flight_tools import get_tool_permission
from typing import Dict, Any, Optional


class PermissionGuard:

    @staticmethod
    def check_tool_permission(
        tool_name: str,
        kwargs: Dict[str, Any],
        user_approval_token: Optional[str] = None
    ) -> HarnessCheckResult:

        level = get_tool_permission(tool_name)

        if level == PermissionLevel.READ or level == PermissionLevel.WRITE:
            return HarnessCheckResult(
                passed=True,
                check_type="Permission",
                details=f"Tool '{tool_name}' có cấp độ quyền [{level.value}]: Được phép thực thi tự động."
            )

        if level == PermissionLevel.CRITICAL:
            provided_token = kwargs.get("user_approval_token") or user_approval_token
            if provided_token == "APPROVED":
                return HarnessCheckResult(
                    passed=True,
                    check_type="Permission",
                    details=f"Tool '{tool_name}' [CRITICAL] đã nhận được Token Phê Duyệt từ Người Dùng ('APPROVED')."
                )
            else:
                return HarnessCheckResult(
                    passed=False,
                    check_type="Permission",
                    details=f"VI PHẠM QUYỀN TRUY CẬP: Tool '{tool_name}' yêu cầu hành động nguy hiểm [CRITICAL] (Thanh toán/Hủy vé) nhưng chưa có sự đồng ý của Con người!",
                    action_required="REQUIRE_USER_APPROVAL"
                )

        return HarnessCheckResult(
            passed=True,
            check_type="Permission",
            details=f"Tool '{tool_name}' mặc định cho phép."
        )
