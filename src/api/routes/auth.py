"""认证路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.api.auth import verify_password, create_session, validate_session

router = APIRouter(prefix="/api", tags=["用户认证"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    success: bool
    username: str = ""
    token: str = ""
    message: str = ""


@router.post("/login", response_model=LoginResponse, summary="用户登录", description="使用 admin/admin123 或 demo/demo123 登录")
async def login(req: LoginRequest):
    if verify_password(req.username, req.password):
        token = create_session(req.username)
        return LoginResponse(success=True, username=req.username, token=token, message="登录成功")
    return LoginResponse(success=False, message="用户名或密码错误")


@router.get("/me", response_model=LoginResponse, summary="验证登录状态",
            description="通过 token 验证当前登录状态")
async def me(token: str = ""):
    username = validate_session(token)
    if username:
        return LoginResponse(success=True, username=username, token=token, message="已登录")
    return LoginResponse(success=False, message="未登录或已过期")
