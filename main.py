import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from evaluation.evaluator import AgentEvaluator


def main():
    print("=" * 70)
    print("Các thành phần hệ thống đã cài đặt:")
    print(" 1. Schema & Data Constraints Validation (schema.py)")
    print(" 2. Mock Airline Tools & Flight Database (mock_db.py, flight_tools.py)")
    print(" 3. Lớp Control Harness: Data, Code Completion, Permission, Hand-off (harness/)")
    print(" 4. ReAct Agent Architecture (agents/react_agent.py)")
    print(" 5. Plan-then-Execute Agent Architecture (agents/plan_execute_agent.py)")
    print(" 6. Hybrid Agent Architecture - Plan+ReAct+Replan (agents/hybrid_agent.py)")
    print("=" * 70)

    print("\n[INFO] Đang khởi chạy Hệ thống Đánh giá Benchmark tự động cho 3 Kiến trúc Agent...")
    evaluator = AgentEvaluator()
    evaluator.run_benchmark()


if __name__ == "__main__":
    main()
