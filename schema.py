from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime


class PermissionLevel(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    CRITICAL = "CRITICAL"

class FlightSearchInput(BaseModel):
    origin: str = Field(..., description="Mã sân bay đi IATA 3 ký tự (ví dụ: SGN, HAN, DAD, PQC, CXR)")
    destination: str = Field(..., description="Mã sân bay đến IATA 3 ký tự (ví dụ: HAN, SGN, DAD, PQC, CXR)")
    departure_date: str = Field(..., description="Ngày đi định dạng YYYY-MM-DD (ví dụ: 2026-10-15)")
    return_date: Optional[str] = Field(None, description="Ngày về định dạng YYYY-MM-DD (nếu khứ hồi)")
    passengers: int = Field(1, ge=1, le=9, description="Số lượng hành khách (từ 1 đến 9)")
    max_budget: Optional[float] = Field(None, gt=0, description="Ngân sách tối đa mỗi vé (VNĐ)")

    @field_validator("origin", "destination")
    @classmethod
    def validate_iata(cls, v: str) -> str:
        v_clean = v.strip().upper()
        if not re.match(r"^[A-Z]{3}$", v_clean):
            raise ValueError(f"Mã sân bay '{v}' không hợp lệ. Phải đúng 3 ký tự IATA (ví dụ: SGN, HAN).")
        return v_clean

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ngày '{v}' không đúng định dạng YYYY-MM-DD.")
        return v


class FlightInfo(BaseModel):
    flight_number: str = Field(..., description="Số hiệu chuyến bay")
    airline: str = Field(..., description="Hãng hàng không")
    origin: str = Field(..., description="Sân bay đi (IATA)")
    destination: str = Field(..., description="Sân bay đến (IATA)")
    departure_time: str = Field(..., description="Giờ cất cánh (YYYY-MM-DD HH:MM)")
    arrival_time: str = Field(..., description="Giờ hạ cánh (YYYY-MM-DD HH:MM)")
    price_vnd: float = Field(..., description="Giá vé 1 người (VNĐ)")
    seats_available: int = Field(..., description="Số ghế còn trống")


class PassengerInfo(BaseModel):
    full_name: str = Field(..., description="Họ và tên hành khách")
    id_card: str = Field(..., description="Số CCCD hoặc Hộ chiếu")

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, v: str) -> str:
        clean_v = v.strip()
        if len(clean_v) < 6 or len(clean_v) > 15:
            raise ValueError(f"Số CCCD/Hộ chiếu '{v}' phải từ 6 đến 15 ký tự.")
        return clean_v


class BookingReservationInput(BaseModel):
    flight_number: str = Field(..., description="Số hiệu chuyến bay muốn đặt")
    departure_date: str = Field(..., description="Ngày khởi hành (YYYY-MM-DD)")
    passengers: List[PassengerInfo] = Field(..., min_items=1, description="Danh sách thông tin hành khách")


class BookingStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class BookingRecord(BaseModel):
    pnr_code: str = Field(..., description="Mã giữ chỗ / PNR 6 ký tự")
    flight_number: str
    origin: str
    destination: str
    departure_date: str
    passengers: List[PassengerInfo]
    total_price_vnd: float
    status: BookingStatus = BookingStatus.PENDING_PAYMENT
    created_at: str
    paid_at: Optional[str] = None



class PaymentInput(BaseModel):
    pnr_code: str = Field(..., description="Mã PNR 6 ký tự cần thanh toán")
    amount_vnd: float = Field(..., gt=0, description="Số tiền cần thanh toán (VNĐ)")
    user_approval_token: Optional[str] = Field(None, description="Token xác nhận phê duyệt từ Người dùng (Bắt buộc cho hành động CRITICAL)")


class PaymentResult(BaseModel):
    success: bool
    pnr_code: str
    transaction_id: Optional[str] = None
    message: str


class HarnessCheckResult(BaseModel):
    passed: bool = Field(..., description="Liệu kiểm tra Harness có vượt qua thành công hay không")
    check_type: str = Field(..., description="Loại kiểm tra: DataConstraint | Permission | CompletionCheck | HandOff")
    details: str = Field(..., description="Chi tiết kết quả kiểm tra")
    action_required: Optional[str] = Field(None, description="Yêu cầu can thiệp (ví dụ: REQUIRE_USER_APPROVAL, HANDOFF_TO_HUMAN, FIX_DATA)")
