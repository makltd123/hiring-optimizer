from fastapi import HTTPException

FREE_LIMITS = {
    "max_projects": 1,
    "max_vacancies_per_project": 3,
    "max_candidates_per_project": 10,
}

PAID_LIMITS = {
    "max_projects": 999,
    "max_vacancies_per_project": 50,
    "max_candidates_per_project": 200,
}

PLAN_PRICES = {
    "start": 2900,
    "business": 7900,
}


def get_limits(plan: str) -> dict:
    return FREE_LIMITS if plan == "free" else PAID_LIMITS


def check_limit(plan: str, resource: str, current_count: int) -> None:
    limits = get_limits(plan)
    limit = limits.get(resource)
    if limit is not None and current_count >= limit:
        raise HTTPException(
            status_code=402,
            detail={
                "upgrade_required": True,
                "limit": limit,
                "resource": resource,
                "message": "Обновите план для снятия ограничений",
                "plans": PLAN_PRICES,
            },
        )
