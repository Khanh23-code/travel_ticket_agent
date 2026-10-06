import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from config import get_llm
from agents.react_agent import build_react_agent
from harness import AgentHarness
from mock_db import reset_mock_db
from langchain_core.messages import HumanMessage

def test_react_agent():
    print("=" * 60)
    print(">>> BAT DAU TEST PHAN 4: ARCHITECTURE 1 - REACT AGENT <<<")
    print("=" * 60)

    llm = get_llm()
    agent_graph = build_react_agent(llm=llm)
    harness = AgentHarness()

    print("\n----------------------------------------------------")
    print("KỊCH BẢN 1: KHÔNG CÓ USER APPROVAL TOKEN")
    print("----------------------------------------------------")
    reset_mock_db()

    initial_state_1 = {
        "messages": [HumanMessage(content="Tôi muốn đặt 1 vé máy bay từ TP.HCM (SGN) đi Hà Nội (HAN) ngày 2026-10-15 cho hành khách NGUYEN VAN A, CCCD: 012345678901. Ngân sách tối đa 3 triệu.")],
        "user_approval_token": None, # Không cấp token thanh toán
        "step_count": 0,
        "harness_logs": [],
        "is_completed": False
    }

    final_state_1 = agent_graph.invoke(initial_state_1)

    print("\nDIỄN BIẾN THỰC THI (MESSAGES TRAJECTORY):")
    for msg in final_state_1["messages"]:
        role = msg.__class__.__name__
        content = msg.content
        print(f"[{role}]: {content[:150]}..." if len(content) > 150 else f"[{role}]: {content}")

    print("\nLOGS KIỂM SOÁT TỪ HARNESS:")
    for log in final_state_1["harness_logs"]:
        print(f"   {log}")

    completion_1 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1, max_budget=3000000.0
    )
    print(f"\nKẾT QUẢ CODE-VERIFIED COMPLETION CHECK:")
    print(f"   Passed: {completion_1.passed} | Details: {completion_1.details}")

    print("\n----------------------------------------------------")
    print("KỊCH BẢN 2: CÓ USER APPROVAL TOKEN ('APPROVED')")
    print("----------------------------------------------------")
    reset_mock_db()

    initial_state_2 = {
        "messages": [HumanMessage(content="Tôi muốn đặt 1 vé máy bay từ TP.HCM (SGN) đi Hà Nội (HAN) ngày 2026-10-15 cho NGUYEN VAN A (CCCD: 012345678901), hãy thanh toán luôn.")],
        "user_approval_token": "APPROVED", # Cấp token thanh toán
        "step_count": 0,
        "harness_logs": [],
        "is_completed": False
    }

    final_state_2 = agent_graph.invoke(initial_state_2)

    print("\nDIỄN BIẾN THỰC THI (MESSAGES TRAJECTORY):")
    for msg in final_state_2["messages"]:
        role = msg.__class__.__name__
        content = msg.content
        print(f"[{role}]: {content[:150]}..." if len(content) > 150 else f"[{role}]: {content}")

    completion_2 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1, max_budget=3000000.0
    )
    print(f"\nKẾT QUẢ CODE-VERIFIED COMPLETION CHECK:")
    print(f"   Passed: {completion_2.passed} | Details: {completion_2.details}")

    print("=" * 60)
    print("TẤT CẢ TEST REACT AGENT ĐÃ HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 60)

if __name__ == "__main__":
    test_react_agent()
