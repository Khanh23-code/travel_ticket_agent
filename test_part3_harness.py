import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from harness import AgentHarness
from mock_db import reset_mock_db, BOOKINGS_DB, generate_pnr_code
from schema import BookingRecord, BookingStatus, PassengerInfo
from datetime import datetime

def test_harness():
    print("=" * 60)
    print(">>> BAT DAU TEST PHAN 3: HARNESS CONTROL FRAMEWORK <<<")
    print("=" * 60)

    harness = AgentHarness()
    reset_mock_db()

    print("\n--- 1. TEST PERMISSION CHECKING ---")
    
    p1 = harness.check_tool_call("search_flights", {"origin": "SGN", "destination": "HAN"})
    print(f"Tool 'search_flights' [READ]: Passed = {p1.passed} | Details: {p1.details}")

    p2 = harness.check_tool_call("process_payment", {"pnr_code": "ABC123", "amount_vnd": 1000000})
    print(f"Tool 'process_payment' [CRITICAL - No Token]: Passed = {p2.passed} | Action: {p2.action_required}")
    print(f"   Details: {p2.details}")

    p3 = harness.check_tool_call("process_payment", {"pnr_code": "ABC123", "amount_vnd": 1000000}, user_approval_token="APPROVED")
    print(f"Tool 'process_payment' [CRITICAL - With Token]: Passed = {p3.passed} | Details: {p3.details}")

    print("\n--- 2. TEST CODE VERIFIED COMPLETION CHECK ---")

    c1 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1
    )
    print(f"Completion Check (Trống DB): Passed = {c1.passed}")
    print(f"   Details: {c1.details}")

    pnr_test = generate_pnr_code()
    BOOKINGS_DB[pnr_test] = BookingRecord(
        pnr_code=pnr_test,
        flight_number="VN210",
        origin="SGN",
        destination="HAN",
        departure_date="2026-10-15",
        passengers=[PassengerInfo(full_name="TEST USER", id_card="123456789")],
        total_price_vnd=2450000.0,
        status=BookingStatus.PENDING_PAYMENT,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    c2 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1
    )
    print(f"Completion Check (Mới PENDING_PAYMENT): Passed = {c2.passed}")
    print(f"   Details: {c2.details}")

    BOOKINGS_DB[pnr_test].status = BookingStatus.CONFIRMED
    c3 = harness.verify_completion(
        origin="SGN", destination="HAN", departure_date="2026-10-15", num_passengers=1
    )
    print(f"Completion Check (Đã CONFIRMED): Passed = {c3.passed}")
    print(f"   Details: {c3.details}")

    print("\n--- 3. TEST HAND-OFF CONTROLLER ---")
    h1 = harness.check_handoff("Chuyên bay sẵn sàng", step_count=3, max_steps=10)
    print(f"Handoff Step 3/10: Passed = {h1.passed} | {h1.details}")

    h2 = harness.check_handoff("Không tìm thấy chuyến bay... với ngân sách <= 1,000,000", step_count=4)
    print(f"Handoff hết vé ngân sách: Passed = {h2.passed} | Action: {h2.action_required}")
    print(f"   Details: {h2.details}")

    print("=" * 60)
    print("TẤT CẢ TEST HARNESS ĐÃ HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 60)

if __name__ == "__main__":
    test_harness()
