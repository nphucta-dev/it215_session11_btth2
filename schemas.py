from pydantic import BaseModel, Field


class SmartHomePlanCreate(BaseModel):
    plan_code: str = Field(..., min_length=1, max_length=50)
    plan_name: str = Field(..., min_length=1, max_length=255)  # không được rỗng
    device_quantity: int = Field(..., gt=0)                    # bắt buộc > 0
    price: float = Field(..., gt=0)                            # bắt buộc > 0