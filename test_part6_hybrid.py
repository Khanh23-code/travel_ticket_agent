import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from config import get_llm
from agents.hybrid_agent import build_hybrid_agent
from harness import AgentHarness
from mock_db import reset_mock_db

def test_hybrid_agent():
    print("=" * 60)
    print(">>> BAT DAU TEST PHAN 6: ARCHITECTURE 3 - HYBRID AGENT <<<")
    print("=" * 60)

    llm = get_llm()
    agent_graph = build_hybrid_agent(llm=llm)
    harness = AgentHarness()

    print("\n----------------------------------------------------")
    print("KỊCH BẢN 1: HYBRID AGENT - KHÔNG CÓ USER APPROVAL TOKEN")
    print("----------------------------------------------------")
    reset_mock_db()

    initial_state_1 = {
        "input_request": "Đặt vé từ SGN đi HAN ngày 2026-10-15 cho NGUYEN VAN A (012345678901)",
        "user_approval_token": None,
        "step_responses": [],
        "messages": [],
        "harness_logs": [],
        "pnr_created": None,
        "replan_count": 0,
        "status": "IN_PROGRESS"
    }

    final_state_1 = agent_graph.invoke(initial_state_1)

    print("\nDIỄN BIẾN LẬP KẾ HOẠCH, DYNAMIC REPLANNING & THỰC THI:")
    for log in final_state_1["harness_logs"]:
        print(f"   {log}")

    print(f"\nTỔNG SỐ LẦN RE-PLANNING: {final_state_1['replan_count']}")
    print(f"KẾ HOẠCH CUỐI CÙNG SAU KHI ĐIỀU CHỈNH ĐỘNG:")
    for idx, s in enumerate(final_state_1["plan"], 1):
        print(f"   {s}")

    completion_1 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1, max_budget=3000000.0
    )
    print(f"\nKẾT QUẢ CODE-VERIFIED COMPLETION CHECK:")
    print(f"   Passed: {completion_1.passed} | Details: {completion_1.details}")

    print("\n----------------------------------------------------")
    print("KỊCH BẢN 2: HYBRID AGENT - CÓ USER APPROVAL TOKEN ('APPROVED')")
    print("----------------------------------------------------")
    reset_mock_db()

    initial_state_2 = {
        "input_request": "Đặt vé từ SGN đi HAN ngày 2026-10-15 cho NGUYEN VAN A (012345678901), hãy thanh toán luôn.",
        "user_approval_token": "APPROVED",
        "step_responses": [],
        "messages": [],
        "harness_logs": [],
        "pnr_created": None,
        "replan_count": 0,
        "status": "IN_PROGRESS"
    }

    final_state_2 = agent_graph.invoke(initial_state_2)

    print("\nDIỄN BIẾN LẬP KẾ HOẠCH & THỰC THI:")
    for log in final_state_2["harness_logs"]:
        print(f"   {log}")

    completion_2 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1, max_budget=3000000.0
    )
    print(f"\nKẾT QUẢ CODE-VERIFIED COMPLETION CHECK:")
    print(f"   Passed: {completion_2.passed} | Details: {completion_2.details}")

    print("=" * 60)
    print("TẤT CẢ TEST HYBRID AGENT ĐÃ HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 60)

if __name__ == "__main__":
    test_hybrid_agent()
