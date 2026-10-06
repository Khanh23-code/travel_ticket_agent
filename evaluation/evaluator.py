import time
from typing import Dict, List, Any
from harness import AgentHarness
from mock_db import reset_mock_db
from agents.react_agent import build_react_agent
from agents.plan_execute_agent import build_plan_execute_agent
from agents.hybrid_agent import build_hybrid_agent
from langchain_core.messages import HumanMessage
from config import get_llm


class AgentEvaluator:
    def __init__(self):
        self.llm = get_llm()
        self.harness = AgentHarness()
        self.react_graph = build_react_agent(self.llm)
        self.plan_exec_graph = build_plan_execute_agent(self.llm)
        self.hybrid_graph = build_hybrid_agent(self.llm)

    def run_benchmark(self) -> Dict[str, Any]:
        architectures = {
            "ReAct Agent": self.react_graph,
            "Plan-then-Execute Agent": self.plan_exec_graph,
            "Hybrid Agent (Lai)": self.hybrid_graph
        }

        scenarios = [
            {
                "id": "TC1",
                "name": "Standard Booking Success",
                "description": "Đặt vé máy bay luồng chuẩn SGN->HAN có token thanh toán 'APPROVED'.",
                "origin": "SGN", "destination": "HAN", "date": "2026-10-15", "passengers": 1,
                "token": "APPROVED", "budget": 3000000.0, "expected_success": True
            },
            {
                "id": "TC2",
                "name": "Permission Checking Guard Blocked",
                "description": "Yêu cầu thanh toán vé nhưng KHÔNG cấp token phê duyệt (Thanh toán bị chặn).",
                "origin": "SGN", "destination": "HAN", "date": "2026-10-15", "passengers": 1,
                "token": None, "budget": 3000000.0, "expected_success": False
            },
            {
                "id": "TC3",
                "name": "Out of Budget Negotiation",
                "description": "Tra cứu vé ngân sách tối đa quá thấp (500,000 VNĐ) -> Kích hoạt Hand-off.",
                "origin": "SGN", "destination": "HAN", "date": "2026-10-15", "passengers": 1,
                "token": "APPROVED", "budget": 500000.0, "expected_success": False
            },
            {
                "id": "TC4",
                "name": "Invalid IATA Airport Code",
                "description": "Mã sân bay đi bị sai ('SAIGON' thay vì 'SGN') -> Trở ngại Ràng buộc Dữ liệu.",
                "origin": "SAIGON", "destination": "HAN", "date": "2026-10-15", "passengers": 1,
                "token": "APPROVED", "budget": 3000000.0, "expected_success": False
            }
        ]

        results = {arch_name: {"total": 0, "passed": 0, "steps": 0, "harness_blocks": 0, "time_ms": 0} for arch_name in architectures}

        print("=" * 75)
        print("BẮT ĐẦU CHẠY BENCHMARK ĐÁNH GIÁ 3 KIẾN TRÚC AGENT")
        print("=" * 75)

        for arch_name, graph in architectures.items():
            print(f"\n>>> RUNNING ARCHITECTURE: {arch_name} <<<")

            for sc in scenarios:
                reset_mock_db()
                start_t = time.time()

                if arch_name == "ReAct Agent":
                    state_input = {
                        "messages": [HumanMessage(content=f"Đặt vé từ {sc['origin']} đi {sc['destination']} ngày {sc['date']}")],
                        "user_approval_token": sc["token"],
                        "step_count": 0,
                        "harness_logs": [],
                        "is_completed": False
                    }
                elif arch_name == "Plan-then-Execute Agent":
                    state_input = {
                        "input_request": f"Đặt vé {sc['origin']}->{sc['destination']} ngày {sc['date']}",
                        "user_approval_token": sc["token"],
                        "step_responses": [],
                        "messages": [],
                        "harness_logs": [],
                        "pnr_created": None
                    }
                else: 
                    state_input = {
                        "input_request": f"Đặt vé {sc['origin']}->{sc['destination']} ngày {sc['date']}",
                        "user_approval_token": sc["token"],
                        "step_responses": [],
                        "messages": [],
                        "harness_logs": [],
                        "pnr_created": None,
                        "replan_count": 0,
                        "status": "IN_PROGRESS"
                    }

                try:
                    final_state = graph.invoke(state_input)
                except Exception as e:
                    print(f"   [{sc['id']}] Exception in execution: {e}")
                    final_state = {"harness_logs": [f"Error: {e}"]}

                elapsed_ms = (time.time() - start_t) * 1000

                completion = self.harness.verify_completion(
                    origin=sc["origin"], destination=sc["destination"], departure_date=sc["date"],
                    num_passengers=sc["passengers"], max_budget=sc["budget"]
                )

                is_passed = (completion.passed == sc["expected_success"])
                harness_blocks = len([l for l in final_state.get("harness_logs", []) if "Passed: False" in l or "BLOCKED" in l])
                steps = len(final_state.get("harness_logs", []))

                results[arch_name]["total"] += 1
                if is_passed:
                    results[arch_name]["passed"] += 1
                results[arch_name]["steps"] += steps
                results[arch_name]["harness_blocks"] += harness_blocks
                results[arch_name]["time_ms"] += elapsed_ms

                status_icon = "PASSED" if is_passed else "FAILED"
                print(f"   - [{sc['id']} - {sc['name']}]: {status_icon} | Time: {elapsed_ms:.1f}ms | Harness Blocks: {harness_blocks}")

        print("\n" + "=" * 75)
        print("BẢNG TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ (EVALUATION REPORT SUMMARY)")
        print("=" * 75)
        print(f"{'Architecture Pattern':<28} | {'Success Rate':<12} | {'Avg Steps':<10} | {'Harness Safety Blocks':<20}")
        print("-" * 75)

        for arch_name, data in results.items():
            success_rate = (data["passed"] / data["total"]) * 100
            avg_steps = data["steps"] / data["total"]
            print(f"{arch_name:<28} | {success_rate:>10.1f}% | {avg_steps:>9.1f} | {data['harness_blocks']:>20}")

        print("=" * 75)
        return results


if __name__ == "__main__":
    evaluator = AgentEvaluator()
    evaluator.run_benchmark()
