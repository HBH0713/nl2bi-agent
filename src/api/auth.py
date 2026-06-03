"""简易用户认证系统"""
import hashlib
import uuid
import time
import threading

# 预设用户（演示用）
_USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "demo": hashlib.sha256("demo123".encode()).hexdigest(),
}

_sessions = {}
_lock = threading.Lock()
SESSION_TTL = 3600  # 1 小时


def verify_password(username: str, password: str) -> bool:
    """验证用户名密码"""
    pw_hash = _USERS.get(username)
    if not pw_hash:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == pw_hash


def create_session(username: str) -> str:
    """创建会话 token"""
    token = uuid.uuid4().hex
    with _lock:
        _sessions[token] = {"username": username, "created": time.time()}
    return token


def validate_session(token: str) -> str | None:
    """验证会话 token，返回用户名或 None"""
    with _lock:
        session = _sessions.get(token)
        if session and (time.time() - session["created"]) < SESSION_TTL:
            return session["username"]
        if session:
            del _sessions[token]
    return None


def list_users() -> list[str]:
    return list(_USERS.keys())


def add_user(username: str, password: str) -> bool:
    if username in _USERS:
        return False
    _USERS[username] = hashlib.sha256(password.encode()).hexdigest()
    return True
