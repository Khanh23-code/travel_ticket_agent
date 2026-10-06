from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from flight_tools import ALL_TOOLS, get_tool_permission
from harness import AgentHarness
from schema import PermissionLevel
import json
import re


class PlanExecuteState(TypedDict):
    input_request: str
    plan: List[str]
    current_step_index: int
    step_responses: List[str]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_approval_token: Optional[str]
    harness_logs: List[str]
    pnr_created: Optional[str]


def build_plan_execute_agent(llm=None):
    """
    Xây dựng Plan-then-Execute Agent với LangGraph.
    """
    harness = AgentHarness()
    tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

    # --- PLANNER NODE ---
    def planner_node(state: PlanExecuteState) -> Dict[str, Any]:
        req = state["input_request"]
        harness_logs = list(state.get("harness_logs", []))

        harness_logs.append("[PLANNER] Bắt đầu lập kế hoạch thực thi (Plan Generation)...")

        if llm:
            planner_prompt = f"""Bạn là Planner Agent chuyên lập kế hoạch cho tác vụ Đặt vé máy bay.
Dựa vào yêu cầu: "{req}"
Hãy trả về kế hoạch dạng danh sách từng bước ngắn gọn. Ví dụ:
1. Tra cứu chuyến bay từ SGN đến HAN
2. Tạo đơn giữ chỗ cho hành khách
3. Thanh toán đơn giữ chỗ với PNR"""
            res = llm.invoke([HumanMessage(content=planner_prompt)])
            plan_steps = [line.strip() for line in res.content.split("\n") if line.strip()]
        else:
            plan_steps = [
                "Bước 1: Tra cứu chuyến bay từ SGN đi HAN ngày 2026-10-15",
                "Bước 2: Tạo đơn giữ chỗ tạm thời cho hành khách NGUYEN VAN A (VN210)",
                "Bước 3: Thanh toán đơn giữ chỗ vé máy bay để hoàn tất xuất vé"
            ]

        harness_logs.append(f"[PLANNER] Đã lập kế hoạch gồm {len(plan_steps)} bước:")
        for idx, step in enumerate(plan_steps, 1):
            harness_logs.append(f"   {step}")

        return {
            "plan": plan_steps,
            "current_step_index": 0,
            "step_responses": [],
            "harness_logs": harness_logs,
            "messages": [AIMessage(content=f"Kế hoạch đặt vé:\n" + "\n".join(plan_steps))]
        }

    # --- EXECUTOR NODE ---
    def executor_node(state: PlanExecuteState) -> Dict[str, Any]:
        plan = state["plan"]
        idx = state["current_step_index"]
        step_text = plan[idx]
        user_token = state.get("user_approval_token")
        harness_logs = list(state.get("harness_logs", []))
        step_responses = list(state.get("step_responses", []))
        pnr_created = state.get("pnr_created")

        harness_logs.append(f"[EXECUTOR] Đang thi hành {step_text}...")

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
        harness_logs.append(f"[HARNESS PERMISSION] Executing '{tool_name}' -> Passed: {perm_check.passed} ({perm_check.details})")

        if not perm_check.passed:
            exec_res = f"[HARNESS BLOCKED]: {perm_check.details}"
        else:
            tool_fn = tools_by_name[tool_name]
            exec_res = str(tool_fn.invoke(kwargs))

            if tool_name == "create_reservation" and "Mã PNR:" in exec_res:
                match = re.search(r"Mã PNR:\s*([A-Z0-9]{6})", exec_res)
                if match:
                    pnr_created = match.group(1)
                    harness_logs.append(f"[STATE UPDATE] Đã lưu mã PNR vừa sinh: {pnr_created}")

        step_responses.append(exec_res)

        return {
            "current_step_index": idx + 1,
            "step_responses": step_responses,
            "harness_logs": harness_logs,
            "pnr_created": pnr_created,
            "messages": [AIMessage(content=f"Kết quả {step_text}:\n{exec_res}")]
        }

    # --- CONDITIONAL EDGE ROUTER ---
    def should_continue(state: PlanExecuteState) -> str:
        idx = state["current_step_index"]
        plan = state["plan"]
        if idx < len(plan):
            return "executor"
        return END

    # --- WORKFLOW ---
    workflow = StateGraph(PlanExecuteState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges("executor", should_continue, ["executor", END])

    return workflow.compile()
