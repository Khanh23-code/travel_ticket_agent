from typing import Dict, List, Optional
from schema import FlightInfo, BookingRecord, BookingStatus, PassengerInfo
from datetime import datetime
import random
import string

MOCK_FLIGHTS: List[Dict] = [
    # SGN -> HAN
    {
        "flight_number": "VN210",
        "airline": "Vietnam Airlines",
        "origin": "SGN",
        "destination": "HAN",
        "departure_time": "2026-10-15 08:00",
        "arrival_time": "2026-10-15 10:15",
        "price_vnd": 2450000.0,
        "seats_available": 15
    },
    {
        "flight_number": "VJ162",
        "airline": "Vietjet Air",
        "origin": "SGN",
        "destination": "HAN",
        "departure_time": "2026-10-15 09:30",
        "arrival_time": "2026-10-15 11:45",
        "price_vnd": 1350000.0,
        "seats_available": 8
    },
    {
        "flight_number": "QH204",
        "airline": "Bamboo Airways",
        "origin": "SGN",
        "destination": "HAN",
        "departure_time": "2026-10-15 14:00",
        "arrival_time": "2026-10-15 16:15",
        "price_vnd": 1850000.0,
        "seats_available": 5
    },
    # HAN -> SGN
    {
        "flight_number": "VN215",
        "airline": "Vietnam Airlines",
        "origin": "HAN",
        "destination": "SGN",
        "departure_time": "2026-10-18 17:00",
        "arrival_time": "2026-10-18 19:15",
        "price_vnd": 2600000.0,
        "seats_available": 10
    },
    {
        "flight_number": "VJ175",
        "airline": "Vietjet Air",
        "origin": "HAN",
        "destination": "SGN",
        "departure_time": "2026-10-18 20:10",
        "arrival_time": "2026-10-18 22:25",
        "price_vnd": 1400000.0,
        "seats_available": 12
    },
    # SGN -> DAD
    {
        "flight_number": "VN112",
        "airline": "Vietnam Airlines",
        "origin": "SGN",
        "destination": "DAD",
        "departure_time": "2026-10-15 07:15",
        "arrival_time": "2026-10-15 08:35",
        "price_vnd": 1650000.0,
        "seats_available": 20
    }
]

BOOKINGS_DB: Dict[str, BookingRecord] = {}


def generate_pnr_code() -> str:
    """Sinh mã PNR ngẫu nhiên 6 ký tự viết hoa (ví dụ: ABC123)."""
    chars = string.ascii_uppercase + string.digits
    while True:
        pnr = ''.join(random.choices(chars, k=6))
        if pnr not in BOOKINGS_DB:
            return pnr


def reset_mock_db():
    """Reset Database về trạng thái ban đầu (dùng cho testing/benchmark)."""
    global BOOKINGS_DB
    BOOKINGS_DB.clear()
    for flight in MOCK_FLIGHTS:
        if flight["flight_number"] == "VN210":
            flight["seats_available"] = 15
        elif flight["flight_number"] == "VJ162":
            flight["seats_available"] = 8
        elif flight["flight_number"] == "QH204":
            flight["seats_available"] = 5
