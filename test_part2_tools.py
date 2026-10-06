import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from flight_tools import (
    search_flights, create_reservation, process_payment,
    get_booking_details, ALL_TOOLS, get_tool_permission
)
from mock_db import BOOKINGS_DB, reset_mock_db, MOCK_FLIGHTS
import re

def test_flight_tools():
    print("=" * 60)
    print(">>> BAT DAU TEST PHAN 2: MOCK TOOLS & DATABASE <<<")
    print("=" * 60)
    
    reset_mock_db()

    print("\n--- 1. KIỂM TRA NHÃN PHÂN QUYỀN (PERMISSION LABELS) ---")
    for t in ALL_TOOLS:
        perm = get_tool_permission(t.name)
        print(f"Tool: {t.name:<22} | Permission: {perm}")

    print("\n--- 2. TEST TOOL SEARCH_FLIGHTS ---")
    res = search_flights.invoke({
        "origin": "SGN",
        "destination": "HAN",
        "departure_date": "2026-10-15",
        "passengers": 2,
        "max_budget": 2000000.0
    })
    print("Kết quả Tra cứu:")
    print(res)

    print("\n--- 3. TEST TOOL CREATE_RESERVATION ---")
    passengers = [
        {"full_name": "NGUYEN VAN A", "id_card": "012345678901"},
        {"full_name": "TRAN THI B", "id_card": "098765432109"}
    ]
    res_booking = create_reservation.invoke({
        "flight_number": "VJ162",
        "departure_date": "2026-10-15",
        "passengers": passengers
    })
    print(res_booking)

    match = re.search(r"Mã PNR:\s*([A-Z0-9]{6})", res_booking)
    if not match:
        print("[FAILED] LỖI: Không lấy được mã PNR!")
        return
    pnr = match.group(1)
    print(f"-> Đã trích xuất mã PNR vừa sinh: {pnr}")

    print("\n--- 4. TEST TOOL GET_BOOKING_DETAILS (TRƯỚC THANH TOÁN) ---")
    details_before = get_booking_details.invoke({"pnr_code": pnr})
    print(details_before)

    print("\n--- 5. TEST TOOL PROCESS_PAYMENT ---")
    pay_res = process_payment.invoke({
        "pnr_code": pnr,
        "amount_vnd": 2700000.0,
        "user_approval_token": "APPROVED"
    })
    print(pay_res)

    print("\n--- 6. TEST TOOL GET_BOOKING_DETAILS (SAU THANH TOÁN) ---")
    details_after = get_booking_details.invoke({"pnr_code": pnr})
    print(details_after)

    print("=" * 60)
    print("TẤT CẢ TEST TOOLS ĐÃ HOÀN THÀNH THÀNH CÔNG!")
    print("=" * 60)

if __name__ == "__main__":
    test_flight_tools()
