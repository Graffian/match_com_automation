from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AccountStatus(str, Enum):
    PENDING = "pending"
    CREATING = "creating"
    VERIFIED = "verified"
    ACTIVE = "active"
    BANNED = "banned"
    ERROR = "error"
    PHONE_VERIFICATION_REQUIRED = "phone_verification_required"


@dataclass
class Account:
    id: int = 0
    email: str = ""
    password: str = ""
    first_name: str = ""
    last_name: str = ""
    gender: str = "male"
    birth_month: str = "01"
    birth_day: str = "01"
    birth_year: str = "1990"
    zip_code: str = ""
    phone: str = ""
    status: AccountStatus = AccountStatus.PENDING
    device_id: str = ""
    proxy: str = ""
    error_message: str = ""
    created_at: str = ""
    verified_at: str = ""
    match_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "password": self.password,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "gender": self.gender,
            "birth_month": self.birth_month,
            "birth_day": self.birth_day,
            "birth_year": self.birth_year,
            "zip_code": self.zip_code,
            "phone": self.phone,
            "status": self.status.value,
            "device_id": self.device_id,
            "proxy": self.proxy,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
            "match_id": self.match_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
