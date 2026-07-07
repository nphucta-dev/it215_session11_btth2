from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime, timezone

from database import get_db
from models import SmartHomePlanModel
from schemas import SmartHomePlanCreate

app = FastAPI()


# ----------------- HELPER -----------------
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_response(status_code: int, message: str, error, data, path: str):
    return {
        "statusCode": status_code,
        "message": message,
        "error": error,
        "data": data,
        "path": path,
        "timestamp": now_iso()
    }


def serialize_plan(plan: SmartHomePlanModel):
    return {
        "id": plan.id,
        "plan_code": plan.plan_code,
        "plan_name": plan.plan_name,
        "device_quantity": plan.device_quantity,
        "price": plan.price
    }


# ----------------- GLOBAL EXCEPTION HANDLERS -----------------
# Đảm bảo mọi lỗi (business hoặc validation) đều trả đúng cấu trúc 6 trường,
# không lộ Stack Trace thô ra ngoài.

ERROR_TEXT_MAP = {
    400: "Bad Request",
    404: "Not Found",
    422: "Unprocessable Entity",
    500: "Internal Server Error"
}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=build_response(
            status_code=exc.status_code,
            message=exc.detail,
            error=ERROR_TEXT_MAP.get(exc.status_code, "Error"),
            data=None,
            path=str(request.url.path)
        )
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Bắt lỗi validate Pydantic (plan_name rỗng, device_quantity <= 0, price <= 0...)
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = f"Dữ liệu không hợp lệ tại trường '{field}': {first_error['msg']}"

    return JSONResponse(
        status_code=422,
        content=build_response(
            status_code=422,
            message=message,
            error="Unprocessable Entity",
            data=None,
            path=str(request.url.path)
        )
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=build_response(
            status_code=500,
            message="Lỗi hệ thống, vui lòng thử lại sau",
            error="Internal Server Error",
            data=None,
            path=str(request.url.path)
        )
    )


# ----------------- API ENDPOINTS -----------------

@app.post("/smart-home-plans", status_code=201)
def create_plan(payload: SmartHomePlanCreate, request: Request, db: Session = Depends(get_db)):
    new_plan = SmartHomePlanModel(
        plan_code=payload.plan_code,
        plan_name=payload.plan_name,
        device_quantity=payload.device_quantity,
        price=payload.price
    )

    try:
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)

    except IntegrityError:
        # Bẫy dữ liệu: plan_code trùng lặp -> vi phạm ràng buộc UNIQUE
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Plan code already exists"
        )

    except SQLAlchemyError:
        # Lỗi xung đột cấu trúc / lỗi hệ thống mạng -> rollback bảo toàn dữ liệu
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Lỗi hệ thống khi lưu dữ liệu"
        )

    return JSONResponse(
        status_code=201,
        content=build_response(
            status_code=201,
            message="Thêm gói thiết bị thành công",
            error=None,
            data=serialize_plan(new_plan),
            path=str(request.url.path)
        )
    )


@app.get("/smart-home-plans")
def get_all_plans(request: Request, db: Session = Depends(get_db)):
    plans = db.query(SmartHomePlanModel).all()  # API danh sách -> dùng .all() là hợp lý
    data = [serialize_plan(p) for p in plans]

    return JSONResponse(
        status_code=200,
        content=build_response(
            status_code=200,
            message="Lấy danh sách thành công",
            error=None,
            data=data,
            path=str(request.url.path)
        )
    )


@app.get("/smart-home-plans/{plan_id}")
def get_plan_detail(plan_id: int, request: Request, db: Session = Depends(get_db)):
    # Tối ưu: chỉ SELECT đúng 1 bản ghi qua .filter().first()
    plan = db.query(SmartHomePlanModel).filter(SmartHomePlanModel.id == plan_id).first()

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    return JSONResponse(
        status_code=200,
        content=build_response(
            status_code=200,
            message="Lấy thông tin gói thiết bị thành công",
            error=None,
            data=serialize_plan(plan),
            path=str(request.url.path)
        )
    )