from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from flight_tools import ALL_TOOLS, get_tool_permission
from harness import AgentHarness
from schema import PermissionLevel
import json
import re


class HybridAgentState(TypedDict):
    input_request: str
    plan: List[str]
    current_step_index: int
    step_responses: List[str]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_approval_token: Optional[str]
    harness_logs: List[str]
    pnr_created: Optional[str]
    replan_count: int
    status: str # "IN_PROGRESS", "REPLANNING", "HANDOFF", "COMPLETED"


def build_hybrid_agent(llm=None):
    """
    Xây dựng Hybrid Agent Graph kết hợp Plan + ReAct + Replanner với LangGraph.
    """
    harness = AgentHarness()
    tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

    # --- INITIAL PLANNER NODE ---
    def planner_node(state: HybridAgentState) -> Dict[str, Any]:
        req = state["input_request"]
        harness_logs = list(state.get("harness_logs", []))

        harness_logs.append("[HYBRID PLANNER] Khởi tạo kế hoạch ban đầu (Initial Plan)...")

        initial_plan = [
            "Bước 1: Tra cứu chuyến bay phù hợp SGN -> HAN",
            "Bước 2: Tạo đơn giữ chỗ tạm thời cho hành khách",
            "Bước 3: Thanh toán xuất vé chính thức"
        ]

        harness_logs.append(f"[HYBRID PLANNER] Đã tạo plan {len(initial_plan)} bước.")

        return {
            "plan": initial_plan,
            "current_step_index": 0,
            "step_responses": [],
            "harness_logs": harness_logs,
            "replan_count": 0,
            "status": "IN_PROGRESS",
            "messages": [AIMessage(content=f"Kế hoạch Lai (Hybrid Plan):\n" + "\n".join(initial_plan))]
        }

    # --- REACT EXECUTOR NODE ---
    def react_executor_node(state: HybridAgentState) -> Dict[str, Any]:
        plan = state["plan"]
        idx = state["current_step_index"]
        step_text = plan[idx] if idx < len(plan) else "Bước hoàn tất"
        user_token = state.get("user_approval_token")
        harness_logs = list(state.get("harness_logs", []))
        step_responses = list(state.get("step_responses", []))
        pnr_created = state.get("pnr_created")

        harness_logs.append(f"[REACT EXECUTOR] Đang thực thi {step_text} bằng ReAct Sub-loop...")

        if "Thanh toán" in step_text or idx == 2:
            tool_name = "process_payment"
            pnr_target = pnr_created if pnr_created else "ABC123"
            kwargs = {
                "pnr_code": pnr_target,
                "amount_vnd": 2450000.0,
                "user_approval_token": user_token
            }
        elif "giữ chỗ" in step_text or idx == 1:
            tool_name = "create_reservation"
            kwargs = {
                "flight_number": "VN210",
                "departure_date": "2026-10-15",
                "passengers": [{"full_name": "NGUYEN VAN A", "id_card": "012345678901"}]
            }
        else: 
            tool_name = "search_flights"
            req_text = state.get("input_request", "")
            origin_arg = "SAIGON" if "SAIGON" in req_text else "SGN"
            kwargs = {"origin": origin_arg, "destination": "HAN", "departure_date": "2026-10-15", "passengers": 1, "max_budget": 3000000.0}

        # HARNESS PERMISSION CHECK
        perm_check = harness.check_tool_call(tool_name, kwargs, user_token)
        harness_logs.append(f"[HARNESS CHECK] Executing '{tool_name}' -> Passed: {perm_check.passed} ({perm_check.details})")

        if not perm_check.passed:
            exec_res = f"[HARNESS BLOCKED]: {perm_check.details}"
        else:
            tool_fn = tools_by_name[tool_name]
            exec_res = str(tool_fn.invoke(kwargs))

            if tool_name == "create_reservation" and "Mã PNR:" in exec_res:
                match = re.search(r"Mã PNR:\s*([A-Z0-9]{6})", exec_res)
                if match:
                    pnr_created = match.group(1)
                    harness_logs.append(f"[STATE UPDATE] Mã PNR ghi nhận: {pnr_created}")

        step_responses.append(exec_res)

        return {
            "step_responses": step_responses,
            "harness_logs": harness_logs,
            "pnr_created": pnr_created,
            "messages": [AIMessage(content=f"Kết quả {step_text}:\n{exec_res}")]
        }

    # --- DYNAMIC REPLANNER NODE ---
    def replanner_node(state: HybridAgentState) -> Dict[str, Any]:
        idx = state["current_step_index"]
        plan = list(state["plan"])
        step_responses = state["step_responses"]
        last_response = step_responses[-1] if step_responses else ""
        harness_logs = list(state.get("harness_logs", []))
        replan_count = state.get("replan_count", 0)

        harness_logs.append(f"[REPLANNER EVALUATION] Đánh giá kết quả sau bước {idx + 1}...")

        if "HARNESS BLOCKED" in last_response or "VI PHẠM QUYỀN" in last_response:
            replan_count += 1
            harness_logs.append(f"[REPLANNER DYNAMIC REPLANNING #{replan_count}] Phát hiện lỗi vi phạm phân quyền thanh toán! Tự động cập nhật kế hoạch: Thêm bước 'Yêu cầu Người dùng cấp Token Phê Duyệt'")
            
            adjusted_plan = plan[:idx + 1] + [
                "Bước bổ sung: Chờ Người dùng xác nhận token 'APPROVED'",
                "Bước thử lại: Thực hiện thanh toán sau khi có Token"
            ]
            return {
                "plan": adjusted_plan,
                "current_step_index": idx + 1,
                "replan_count": replan_count,
                "status": "HANDOFF",
                "harness_logs": harness_logs
            }

        harness_logs.append(f"[REPLANNER] Bước {idx + 1} hoàn thành tốt. Tiếp tục kế hoạch.")
        next_idx = idx + 1
        new_status = "COMPLETED" if next_idx >= len(plan) else "IN_PROGRESS"

        return {
            "current_step_index": next_idx,
            "status": new_status,
            "harness_logs": harness_logs
        }

    # --- CONDITIONAL ROUTER ---
    def should_continue(state: HybridAgentState) -> str:
        status = state.get("status")
        idx = state.get("current_step_index", 0)
        plan = state.get("plan", [])

        if status == "HANDOFF" or status == "COMPLETED" or idx >= len(plan):
            return END

        return "react_executor"

    # --- WORKFLOW ---
    workflow = StateGraph(HybridAgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("react_executor", react_executor_node)
    workflow.add_node("replanner", replanner_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "react_executor")
    workflow.add_edge("react_executor", "replanner")
    workflow.add_conditional_edges("replanner", should_continue, ["react_executor", END])

    return workflow.compile()
