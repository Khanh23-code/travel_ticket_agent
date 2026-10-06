from schema import HarnessCheckResult, FlightSearchInput, BookingReservationInput
from pydantic import ValidationError
from typing import Dict, Any, Optional


class DataConstraintValidator:
    @staticmethod
    def validate_search_input(params: Dict[str, Any]) -> HarnessCheckResult:
        try:
            FlightSearchInput(**params)
            return HarnessCheckResult(
                passed=True,
                check_type="DataConstraint",
                details="Dữ liệu tra cứu chuyến bay hợp lệ."
            )
        except ValidationError as e:
            return HarnessCheckResult(
                passed=False,
                check_type="DataConstraint",
                details=f"Vi phạm Data Constraint Tra cứu: {e.errors()[0]['msg']}",
                action_required="FIX_DATA"
            )

    @staticmethod
    def validate_booking_input(params: Dict[str, Any]) -> HarnessCheckResult:
        try:
            BookingReservationInput(**params)
            return HarnessCheckResult(
                passed=True,
                check_type="DataConstraint",
                details="Dữ liệu đặt vé hợp lệ."
            )
        except ValidationError as e:
            return HarnessCheckResult(
                passed=False,
                check_type="DataConstraint",
                details=f"Vi phạm Data Constraint Đặt vé: {e.errors()[0]['msg']}",
                action_required="FIX_DATA"
            )
