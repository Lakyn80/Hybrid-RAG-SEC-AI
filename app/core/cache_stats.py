from app.retrieval import resources


def build_stats_key(namespace: str) -> str:
    return f"stats:{namespace}"


def increment_cache_stat(namespace: str, metric: str, amount: int = 1) -> None:
    try:
        resources.get_redis_client().hincrby(build_stats_key(namespace), metric, amount)
    except Exception:
        return


def get_cache_stats(namespace: str) -> dict[str, int]:
    try:
        raw = resources.get_redis_client().hgetall(build_stats_key(namespace))
    except Exception:
        return {}

    stats = {}
    for key, value in raw.items():
        try:
            stats[str(key)] = int(value)
        except Exception:
            continue
    return stats


def reset_cache_stats(namespace: str) -> None:
    try:
        resources.get_redis_client().delete(build_stats_key(namespace))
    except Exception:
        return
