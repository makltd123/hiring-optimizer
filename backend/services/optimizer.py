import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linear_sum_assignment, milp


def hungarian_assignment(match_matrix: np.ndarray) -> tuple:
    cost_matrix = -match_matrix
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return row_ind, col_ind


def optimize_with_fot_constraint(
    match_matrix: np.ndarray,
    salary_expectations: list,
    salary_maxes: list,
    fot_limit: float,
) -> dict:
    n_candidates, n_vacancies = match_matrix.shape
    n = n_candidates * n_vacancies

    # Целевая функция: минимизировать -score (чтобы максимизировать score)
    c = -match_matrix.flatten()

    # Каждый кандидат назначен не более чем на одну вакансию
    A_cand = np.zeros((n_candidates, n))
    for i in range(n_candidates):
        A_cand[i, i * n_vacancies:(i + 1) * n_vacancies] = 1
    b_cand = np.ones(n_candidates)

    # Каждая вакансия закрыта не более чем одним кандидатом
    A_vac = np.zeros((n_vacancies, n))
    for j in range(n_vacancies):
        for i in range(n_candidates):
            A_vac[j, i * n_vacancies + j] = 1
    b_vac = np.ones(n_vacancies)

    # ФОТ-ограничение
    salaries = np.array([
        salary_expectations[i] if salary_expectations[i] else 0
        for i in range(n_candidates)
        for _ in range(n_vacancies)
    ])
    A_fot = salaries.reshape(1, n)
    b_fot = np.array([fot_limit])

    A_ub = np.vstack([A_cand, A_vac, A_fot])
    b_ub = np.concatenate([b_cand, b_vac, b_fot])

    # Целочисленная задача: с ФОТ-ограничением непрерывная релаксация даёт дробные
    # назначения, и их округление нарушает бюджет или ставит кандидата на две вакансии.
    result = milp(
        c,
        constraints=LinearConstraint(A_ub, -np.inf, b_ub),
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
    )

    if result.status != 0:
        min_fot = _compute_min_fot(match_matrix, salary_expectations)
        raise ValueError(f"Не удалось решить задачу с ФОТ-лимитом. ФОТ без ограничения: {min_fot:.0f} ₽")

    x = np.round(result.x).reshape(n_candidates, n_vacancies)
    assignment = {}
    for j in range(n_vacancies):
        chosen = np.flatnonzero(x[:, j] > 0.5)
        assignment[j] = int(chosen[0]) if len(chosen) else None
    return assignment


def _compute_min_fot(match_matrix: np.ndarray, salary_expectations: list) -> float:
    """ФОТ оптимального назначения без бюджетного ограничения."""
    row_ind, _ = linear_sum_assignment(-match_matrix)
    return float(sum(salary_expectations[i] or 0 for i in row_ind))


def run_optimization(
    match_matrix: np.ndarray,
    candidates: list,
    vacancies: list,
    fot_limit: float | None,
) -> dict:
    n_c, n_v = match_matrix.shape

    if fot_limit:
        salary_expectations = [c.salary_expectation or 0 for c in candidates]
        salary_maxes = [v.salary_max or float("inf") for v in vacancies]
        assignment_indices = optimize_with_fot_constraint(
            match_matrix, salary_expectations, salary_maxes, fot_limit
        )
    else:
        row_ind, col_ind = hungarian_assignment(match_matrix)
        assignment_indices = {int(col_ind[k]): int(row_ind[k]) for k in range(len(row_ind))}

    # Определяем резервных кандидатов и незакрытые вакансии
    assigned_candidates = set(v for v in assignment_indices.values() if v is not None)
    reserve = [candidates[i].id for i in range(n_c) if i not in assigned_candidates]
    uncovered = [vacancies[j].id for j in range(n_v) if assignment_indices.get(j) is None]

    # Переводим индексы в ID
    assignment_by_id = {}
    for vac_idx, cand_idx in assignment_indices.items():
        vac_id = str(vacancies[vac_idx].id)
        assignment_by_id[vac_id] = candidates[cand_idx].id if cand_idx is not None else None

    explanation = build_explanation(assignment_indices, candidates, vacancies, match_matrix)
    total_cost = _compute_total_cost(assignment_indices, candidates)

    return {
        "assignment": assignment_by_id,
        "match_scores": {
            str(vacancies[j].id): {
                str(candidates[i].id): round(float(match_matrix[i][j]), 3)
                for i in range(n_c)
            }
            for j in range(n_v)
        },
        "explanation": explanation,
        "total_cost": total_cost,
        "reserve": reserve,
        "uncovered_vacancies": uncovered,
    }


def build_explanation(
    assignment: dict,
    candidates: list,
    vacancies: list,
    match_matrix: np.ndarray,
) -> str:
    lines = []
    for vac_idx, cand_idx in assignment.items():
        vac = vacancies[int(vac_idx)]
        if cand_idx is None:
            lines.append(f"Вакансия «{vac.title}»: не закрыта — недостаточно кандидатов или бюджета")
        else:
            cand = candidates[int(cand_idx)]
            score = match_matrix[int(cand_idx)][int(vac_idx)]
            lines.append(
                f"{cand.display_name} → «{vac.title}»: соответствие {score:.0%}"
                + (f", ожидания {cand.salary_expectation:,.0f} ₽" if cand.salary_expectation else "")
            )
    return "\n".join(lines)


def _compute_total_cost(assignment: dict, candidates: list) -> float:
    total = 0.0
    for cand_idx in assignment.values():
        if cand_idx is not None and candidates[int(cand_idx)].salary_expectation:
            total += candidates[int(cand_idx)].salary_expectation
    return total
