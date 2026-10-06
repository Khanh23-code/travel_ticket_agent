import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from schema import FlightSearchInput, PassengerInfo, BookingReservationInput, PermissionLevel
from pydantic import ValidationError

def test_schema_validation():
    print("=" * 60)
    print(">>> BAT DAU TEST PHAN 1: SCHEMA & DATA CONSTRAINTS <<<")
    print("=" * 60)

    try:
        valid_search = FlightSearchInput(
            origin="sgn",
            destination="HAN",
            departure_date="2026-10-15",
            passengers=2,
            max_budget=3000000.0
        )
        print("[PASSED] Valid Search Data Input:")
        print(f"   Origin: {valid_search.origin} | Destination: {valid_search.destination}")
        print(f"   Date: {valid_search.departure_date} | Passengers: {valid_search.passengers} | Budget: {valid_search.max_budget:,.0f} VNĐ")
    except ValidationError as e:
        print("[FAILED] Valid search input errored unexpectedly:", e)

    print("-" * 60)

    try:
        invalid_iata = FlightSearchInput(
            origin="SAIGON",
            destination="HAN",
            departure_date="2026-10-15"
        )
        print("[FAILED] Invalid IATA code was allowed!")
    except ValidationError as e:
        print("[PASSED] Catch invalid IATA code correctly:")
        print(f"   Error message: {e.errors()[0]['msg']}")

    print("-" * 60)

    try:
        invalid_date = FlightSearchInput(
            origin="SGN",
            destination="HAN",
            departure_date="15/10/2026" 
        )
        print("[FAILED] Invalid date format was allowed!")
    except ValidationError as e:
        print("[PASSED] Catch invalid Date Format correctly:")
        print(f"   Error message: {e.errors()[0]['msg']}")

    print("-" * 60)

    try:
        passenger = PassengerInfo(
            full_name="NGUYEN VAN A",
            id_card="123456789012"
        )
        booking = BookingReservationInput(
            flight_number="VN123",
            departure_date="2026-10-15",
            passengers=[passenger]
        )
        print("[PASSED] BookingReservationInput verified:")
        print(f"   Flight: {booking.flight_number} | Passenger: {booking.passengers[0].full_name}")
    except ValidationError as e:
        print("[FAILED] Passenger info errored:", e)

    print("=" * 60)
    print("TẤT CẢ TEST SCHEMA ĐÃ HOÀN THÀNH!")
    print("=" * 60)

if __name__ == "__main__":
    test_schema_validation()
