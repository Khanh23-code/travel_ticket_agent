from schema import HarnessCheckResult, BookingStatus
from mock_db import BOOKINGS_DB
from typing import Dict, Any, Optional, List


class CodeVerifiedCompletionChecker:
    @staticmethod
    def verify_booking_completed(
        origin: str,
        destination: str,
        departure_date: str,
        num_passengers: int,
        max_budget: Optional[float] = None,
        expected_pnr: Optional[str] = None
    ) -> HarnessCheckResult:
        target_pnr = expected_pnr.upper() if expected_pnr else None

        candidate_bookings = []
        for pnr, record in BOOKINGS_DB.items():
            if target_pnr and pnr != target_pnr:
                continue
            if record.origin == origin.upper() and record.destination == destination.upper():
                if record.departure_date == departure_date and len(record.passengers) == num_passengers:
                    candidate_bookings.append(record)

        if not candidate_bookings:
            return HarnessCheckResult(
                passed=False,
                check_type="CompletionCheck",
                details=f"CODE ASSERTION FAILED: Không tìm thấy Đơn đặt vé nào trong Database cho hành trình {origin}->{destination} ngày {departure_date} đủ {num_passengers} hành khách."
            )

        confirmed_booking = None
        for b in candidate_bookings:
            if b.status == BookingStatus.CONFIRMED:
                confirmed_booking = b
                break

        if not confirmed_booking:
            latest_status = candidate_bookings[0].status.value
            return HarnessCheckResult(
                passed=False,
                check_type="CompletionCheck",
                details=f"CODE ASSERTION FAILED: Đơn đặt vé (PNR {candidate_bookings[0].pnr_code}) đã được tạo nhưng chưa hoàn tất thanh toán (Trạng thái hiện tại: {latest_status})."
            )

        if max_budget is not None:
            price_per_person = confirmed_booking.total_price_vnd / num_passengers
            if price_per_person > max_budget:
                return HarnessCheckResult(
                    passed=False,
                    check_type="CompletionCheck",
                    details=f"CODE ASSERTION FAILED: Vé đã được đặt thành công (PNR {confirmed_booking.pnr_code}) nhưng giá vé ({price_per_person:,.0f} VNĐ/người) vượt quá ngân sách tối đa ({max_budget:,.0f} VNĐ)."
                )

        return HarnessCheckResult(
            passed=True,
            check_type="CompletionCheck",
            details=f"CODE ASSERTION PASSED: Đơn vé PNR [{confirmed_booking.pnr_code}] đã được XUẤT VÉ THÀNH CÔNG (CONFIRMED) cho {num_passengers} hành khách với tổng tiền {confirmed_booking.total_price_vnd:,.0f} VNĐ!"
        )
