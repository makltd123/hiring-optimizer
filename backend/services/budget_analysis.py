import numpy as np
from services.optimizer import optimize_with_fot_constraint


def analyze_budget_scenarios(
    candidates: list,
    vacancies: list,
    match_matrix: np.ndarray,
    steps: int = 10,
) -> list:
    salaries = [c.salary_expectation or 0 for c in candidates]
    salary_maxes = [v.salary_max or float("inf") for v in vacancies]
    n_vacancies = len(vacancies)

    positive_salaries = sorted(s for s in salaries if s > 0)
    if not positive_salaries or n_vacancies == 0:
        return []

    min_fot = sum(positive_salaries[:n_vacancies])
    max_fot = sum(salaries)

    if max_fot <= min_fot:
        max_fot = min_fot * 2

    step_size = (max_fot - min_fot) / steps
    scenarios = []

    for i in range(steps + 1):
        fot_limit = min_fot + step_size * i
        try:
            assignment = optimize_with_fot_constraint(
                match_matrix, salaries, salary_maxes, fot_limit
            )
            assigned_indices = [v for v in assignment.values() if v is not None]
            coverage = len(assigned_indices) / n_vacancies if n_vacancies > 0 else 0.0
            total_cost = sum(
                salaries[idx] for idx in assigned_indices if idx < len(salaries)
            )
            scenarios.append({
                "fot_limit": round(fot_limit),
                "coverage": round(coverage, 3),
                "assigned_count": len(assigned_indices),
                "total_cost": round(total_cost),
            })
        except ValueError:
            scenarios.append({
                "fot_limit": round(fot_limit),
                "coverage": 0.0,
                "assigned_count": 0,
                "total_cost": 0,
            })

    return scenarios
