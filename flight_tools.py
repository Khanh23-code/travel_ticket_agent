from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from schema import (
    FlightSearchInput, FlightInfo, PassengerInfo,
    BookingReservationInput, BookingRecord, BookingStatus,
    PaymentInput, PaymentResult, PermissionLevel
)
from mock_db import MOCK_FLIGHTS, BOOKINGS_DB, generate_pnr_code
from datetime import datetime
import json


TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
    "search_flights": PermissionLevel.READ,
    "create_reservation": PermissionLevel.WRITE,
    "process_payment": PermissionLevel.CRITICAL,
    "cancel_booking": PermissionLevel.CRITICAL,
    "get_booking_details": PermissionLevel.READ,
}

def get_tool_permission(tool_name: str) -> PermissionLevel:
    """Trả về cấp độ phân quyền của một Tool theo tên."""
    return TOOL_PERMISSIONS.get(tool_name, PermissionLevel.READ)


@tool
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    max_budget: Optional[float] = None
) -> str:
    """
    Tra cứu danh sách các chuyến bay khả dụng theo tiêu chí.
    - origin: Mã sân bay đi 3 ký tự (SGN, HAN, DAD...)
    - destination: Mã sân bay đến 3 ký tự (HAN, SGN, DAD...)
    - departure_date: Ngày đi dạng YYYY-MM-DD
    - passengers: Số hành khách (mặc định 1)
    - max_budget: Ngân sách tối đa VNĐ (không bắt buộc)
    """
    try:
        search_req = FlightSearchInput(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
            max_budget=max_budget
        )
    except Exception as e:
        return f"LỖI RÀNG BUỘC DỮ LIỆU INPUT: {str(e)}"

    results = []
    for flight in MOCK_FLIGHTS:
        if flight["origin"] == search_req.origin and flight["destination"] == search_req.destination:
            if flight["departure_time"].startswith(search_req.departure_date):
                if flight["seats_available"] >= search_req.passengers:
                    if search_req.max_budget is None or flight["price_vnd"] <= search_req.max_budget:
                        results.append(flight)

    if not results:
        budget_str = f" với ngân sách <= {max_budget:,.0f} VNĐ" if max_budget else ""
        return f"Không tìm thấy chuyến bay từ {search_req.origin} đến {search_req.destination} ngày {search_req.departure_date}{budget_str} đủ {passengers} ghế."

    res_str = f"Tìm thấy {len(results)} chuyến bay phù hợp:\n"
    for idx, f in enumerate(results, 1):
        res_str += f"{idx}. Số hiệu: {f['flight_number']} | Hãng: {f['airline']} | Giờ: {f['departure_time']} -> {f['arrival_time']} | Giá: {f['price_vnd']:,.0f} VNĐ/vé | Ghế trống: {f['seats_available']}\n"
    return res_str


@tool
def create_reservation(
    flight_number: str,
    departure_date: str,
    passengers: List[Dict[str, str]]
) -> str:
    """
    Tạo đơn giữ chỗ tạm thời cho chuyến bay. Sinh ra mã PNR 6 ký tự.
    - flight_number: Số hiệu chuyến bay (ví dụ: VN210)
    - departure_date: Ngày đi (YYYY-MM-DD)
    - passengers: Danh sách thông tin hành khách dạng list of dict, ví dụ: [{'full_name': 'NGUYEN VAN A', 'id_card': '123456789'}]
    """
    try:
        passenger_objs = [PassengerInfo(**p) for p in passengers]
        res_req = BookingReservationInput(
            flight_number=flight_number.upper(),
            departure_date=departure_date,
            passengers=passenger_objs
        )
    except Exception as e:
        return f"LỖI DATA CONSTRAINT (TẠO GIỮ CHỖ): {str(e)}"

    target_flight = None
    for f in MOCK_FLIGHTS:
        if f["flight_number"] == res_req.flight_number and f["departure_time"].startswith(res_req.departure_date):
            target_flight = f
            break

    if not target_flight:
        return f"LỖI: Không tìm thấy chuyến bay {res_req.flight_number} ngày {res_req.departure_date}."

    num_passengers = len(res_req.passengers)
    if target_flight["seats_available"] < num_passengers:
        return f"LỖI: Chuyến bay {res_req.flight_number} chỉ còn {target_flight['seats_available']} ghế trống (yêu cầu {num_passengers} ghế)."

    target_flight["seats_available"] -= num_passengers
    pnr = generate_pnr_code()
    total_price = target_flight["price_vnd"] * num_passengers

    booking_record = BookingRecord(
        pnr_code=pnr,
        flight_number=target_flight["flight_number"],
        origin=target_flight["origin"],
        destination=target_flight["destination"],
        departure_date=res_req.departure_date,
        passengers=res_req.passengers,
        total_price_vnd=total_price,
        status=BookingStatus.PENDING_PAYMENT,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    BOOKINGS_DB[pnr] = booking_record

    return (
        f"[OK] TẠO ĐƠN GIỮ CHỖ THÀNH CÔNG!\n"
        f"- Mã PNR: {pnr}\n"
        f"- Chuyến bay: {target_flight['flight_number']} ({target_flight['origin']} -> {target_flight['destination']})\n"
        f"- Ngày đi: {res_req.departure_date}\n"
        f"- Số hành khách: {num_passengers}\n"
        f"- Tổng tiền: {total_price:,.0f} VNĐ\n"
        f"- Trạng thái: {booking_record.status.value}\n"
        f"[NOTE] Vui lòng hoàn tất thanh toán (gọi tool process_payment) để xuất vé chính thức."
    )


@tool
def process_payment(
    pnr_code: str,
    amount_vnd: float,
    user_approval_token: Optional[str] = None
) -> str:
    """
    Thanh toán đơn đặt vé và xuất vé chính thức (Yêu cầu quyền CRITICAL).
    - pnr_code: Mã PNR 6 ký tự
    - amount_vnd: Số tiền cần thanh toán VNĐ
    - user_approval_token: Token hoặc chuỗi xác nhận từ người dùng ("APPROVED")
    """
    pnr_clean = pnr_code.strip().upper()
    if pnr_clean not in BOOKINGS_DB:
        return f"LỖI THANH TOÁN: Không tìm thấy mã PNR '{pnr_clean}' trong hệ thống."

    booking = BOOKINGS_DB[pnr_clean]

    if booking.status == BookingStatus.CONFIRMED:
        return f"THÔNG BÁO: Đơn PNR '{pnr_clean}' đã được thanh toán trước đó rồi."

    if abs(amount_vnd - booking.total_price_vnd) > 1.0:
        return f"LỖI THANH TOÁN: Số tiền thanh toán ({amount_vnd:,.0f} VNĐ) không khớp với giá vé ({booking.total_price_vnd:,.0f} VNĐ)."

    booking.status = BookingStatus.CONFIRMED
    booking.paid_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"[SUCCESS] THANH TOÁN THÀNH CÔNG VÀ XUẤT VÉ THÀNH CÔNG!\n"
        f"- Mã PNR: {pnr_clean}\n"
        f"- Chuyến bay: {booking.flight_number}\n"
        f"- Số tiền đã thanh toán: {amount_vnd:,.0f} VNĐ\n"
        f"- Trạng thái mới: {booking.status.value}\n"
        f"- Mã giao dịch ngân hàng: TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )


@tool
def cancel_booking(
    pnr_code: str,
    user_approval_token: Optional[str] = None
) -> str:
    """
    Hủy đơn đặt vé (Yêu cầu quyền CRITICAL).
    - pnr_code: Mã PNR cần hủy
    - user_approval_token: Chuỗi xác nhận từ người dùng ("APPROVED")
    """
    pnr_clean = pnr_code.strip().upper()
    if pnr_clean not in BOOKINGS_DB:
        return f"LỖI: Không tìm thấy mã PNR '{pnr_clean}'."

    booking = BOOKINGS_DB[pnr_clean]
    booking.status = BookingStatus.CANCELLED
    return f"[OK] HỦY ĐƠN VÉ THÀNH CÔNG! Mã PNR {pnr_clean} đã chuyển sang trạng thái CANCELLED."


@tool
def get_booking_details(pnr_code: str) -> str:
    """
    Tra cứu thông tin chi tiết của một mã PNR (Quyền READ).
    - pnr_code: Mã PNR 6 ký tự
    """
    pnr_clean = pnr_code.strip().upper()
    if pnr_clean not in BOOKINGS_DB:
        return f"Không tìm thấy dữ liệu cho mã PNR '{pnr_clean}'."

    b = BOOKINGS_DB[pnr_clean]
    passengers_str = ", ".join([f"{p.full_name} ({p.id_card})" for p in b.passengers])
    return (
        f"THÔNG TIN ĐƠN PNR [{b.pnr_code}]:\n"
        f"- Chuyến bay: {b.flight_number} ({b.origin} -> {b.destination})\n"
        f"- Ngày đi: {b.departure_date}\n"
        f"- Hành khách: {passengers_str}\n"
        f"- Tổng tiền: {b.total_price_vnd:,.0f} VNĐ\n"
        f"- Trạng thái: {b.status.value}\n"
        f"- Thời gian tạo: {b.created_at}"
    )


ALL_TOOLS = [search_flights, create_reservation, process_payment, cancel_booking, get_booking_details]
