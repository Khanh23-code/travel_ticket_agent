from typing import TypedDict, Annotated, Sequence, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from flight_tools import ALL_TOOLS, get_tool_permission
from harness import AgentHarness
from schema import PermissionLevel
import json
import re


class ReActAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_approval_token: Optional[str]
    step_count: int
    harness_logs: List[str]
    is_completed: bool


REACT_SYSTEM_PROMPT = """Bạn là Agent chuyên nghiệp hỗ trợ đặt vé máy bay tự động.
Quy trình đặt vé máy bay tiêu chuẩn:
1. Tra cứu chuyến bay phù hợp theo yêu cầu người dùng (sử dụng tool search_flights).
2. Tạo đơn giữ chỗ tạm thời (sử dụng tool create_reservation với danh sách hành khách đầy đủ).
3. Thanh toán đơn giữ chỗ để xuất vé (sử dụng tool process_payment). Chú ý: Tool này yêu cầu quyền CRITICAL và phải truyền user_approval_token (nếu người dùng đã chấp nhận thanh toán).

Luôn suy nghĩ cẩn thận trước khi gọi tool. Không bịa đặt thông tin chuyến bay."""



def build_react_agent(llm=None):
    harness = AgentHarness()
    tools_by_name = {tool.name: tool for tool in ALL_TOOLS}

    llm_with_tools = llm.bind_tools(ALL_TOOLS) if llm else None

    # --- AGENT REASONING NODE ---
    def agent_node(state: ReActAgentState) -> Dict[str, Any]:
        messages = list(state["messages"])
        step_count = state.get("step_count", 0) + 1
        harness_logs = list(state.get("harness_logs", []))

        if not messages or not isinstance(messages[0], SystemMessage := type(HumanMessage(content=""))):
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=REACT_SYSTEM_PROMPT)] + messages

        if llm_with_tools:
            response = llm_with_tools.invoke(messages)
            return {
                "messages": [response],
                "step_count": step_count,
                "harness_logs": harness_logs
            }
        else:
            last_msg = messages[-1].content if messages else ""
            harness_logs.append(f"[Step {step_count}] Deterministic ReAct Reasoning Engine")

            tool_messages_count = len([m for m in messages if isinstance(m, ToolMessage)])

            if tool_messages_count == 0:
                first_msg_content = messages[0].content if messages else ""
                origin_arg = "SAIGON" if "SAIGON" in first_msg_content else "SGN"
                call = {
                    "name": "search_flights",
                    "args": {"origin": origin_arg, "destination": "HAN", "departure_date": "2026-10-15", "passengers": 1, "max_budget": 3000000.0},
                    "id": f"call_search_{step_count}"
                }
                ai_msg = AIMessage(content="Tôi sẽ bắt đầu tra cứu chuyến bay SGN -> HAN ngày 2026-10-15.", tool_calls=[call])
            elif tool_messages_count == 1:
                call = {
                    "name": "create_reservation",
                    "args": {
                        "flight_number": "VN210",
                        "departure_date": "2026-10-15",
                        "passengers": [{"full_name": "NGUYEN VAN A", "id_card": "012345678901"}]
                    },
                    "id": f"call_res_{step_count}"
                }
                ai_msg = AIMessage(content="Tôi đã chọn chuyến bay VN210 và sẽ tiến hành tạo giữ chỗ.", tool_calls=[call])
            elif tool_messages_count >= 2 and not any(isinstance(m, ToolMessage) and "THANH TOÁN THÀNH CÔNG" in m.content for m in messages):
                pnr_found = "ABC123"
                for m in messages:
                    if isinstance(m, ToolMessage) and "Mã PNR:" in m.content:
                        match = re.search(r"Mã PNR:\s*([A-Z0-9]{6})", m.content)
                        if match:
                            pnr_found = match.group(1)

                call = {
                    "name": "process_payment",
                    "args": {
                        "pnr_code": pnr_found,
                        "amount_vnd": 2450000.0,
                        "user_approval_token": state.get("user_approval_token")
                    },
                    "id": f"call_pay_{step_count}"
                }
                ai_msg = AIMessage(content=f"Tôi sẽ tiến hành thanh toán cho đơn giữ chỗ PNR {pnr_found}.", tool_calls=[call])
            else:
                ai_msg = AIMessage(content="Tác vụ đặt vé và thanh toán đã hoàn tất thành công!")

            return {
                "messages": [ai_msg],
                "step_count": step_count,
                "harness_logs": harness_logs
            }

    # --- HARNESS PROTECTED TOOLS NODE ---
    def tools_node(state: ReActAgentState) -> Dict[str, Any]:
        last_message = state["messages"][-1]
        user_token = state.get("user_approval_token")
        harness_logs = list(state.get("harness_logs", []))
        tool_messages = []

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                t_id = tool_call["id"]

                # HARNESS PERMISSION GUARD CHECK
                perm_check = harness.check_tool_call(t_name, t_args, user_token)
                harness_logs.append(f"[HARNESS PERMISSION] Tool: {t_name} -> Passed: {perm_check.passed} ({perm_check.details})")

                if not perm_check.passed:
                    err_msg = f"[HARNESS GUARD BLOCKED]: {perm_check.details}. Vui lòng cung cấp token phê duyệt người dùng."
                    tool_messages.append(ToolMessage(content=err_msg, tool_call_id=t_id))
                    continue

                # THỰC THI TOOL
                tool_fn = tools_by_name[t_name]
                result_output = tool_fn.invoke(t_args)
                tool_messages.append(ToolMessage(content=str(result_output), tool_call_id=t_id))

        return {
            "messages": tool_messages,
            "harness_logs": harness_logs
        }

    # --- CONDITIONAL EDGE ROUTER ---
    def should_continue(state: ReActAgentState) -> str:
        last_message = state["messages"][-1]
        step_count = state.get("step_count", 0)

        if step_count >= 10:
            return END

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        return END

    # --- LANGGRAPH WORKFLOW ---
    workflow = StateGraph(ReActAgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile()
