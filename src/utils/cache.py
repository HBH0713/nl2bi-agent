"""查询缓存：避免重复查询浪费 API 费用"""
import hashlib
import json
import time
import threading

_cache = {}
_lock = threading.Lock()
_cache_ttl = 300  # 5 分钟过期


def _cache_key(query: str) -> str:
    return hashlib.md5(query.strip().lower().encode()).hexdigest()


def get_cached(query: str) -> dict | None:
    """获取缓存的查询结果"""
    key = _cache_key(query)
    with _lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < _cache_ttl:
            return entry["data"]
        elif entry:
            del _cache[key]
    return None


def set_cache(query: str, data: dict) -> None:
    """缓存查询结果"""
    key = _cache_key(query)
    with _lock:
        _cache[key] = {"data": data, "ts": time.time()}


def get_cache_stats() -> dict:
    """获取缓存统计"""
    with _lock:
        return {
            "entries": len(_cache),
            "queries": list(_cache.keys())[:10],
        }
