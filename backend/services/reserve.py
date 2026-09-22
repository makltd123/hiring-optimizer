import numpy as np


def compute_reserve_list(
    candidates: list,
    vacancies: list,
    match_matrix: np.ndarray,
    assignment: dict,
) -> dict:
    """
    assignment: {vac_idx: cand_idx or None}
    """
    assigned_candidates = {v for v in assignment.values() if v is not None}
    reserve = []

    for candidate_idx, candidate in enumerate(candidates):
        if candidate_idx in assigned_candidates:
            continue

        scores = match_matrix[candidate_idx]
        best_vacancy_idx = int(np.argmax(scores))
        best_score = float(scores[best_vacancy_idx])

        competitor_idx = assignment.get(best_vacancy_idx)
        competitor = candidates[competitor_idx] if competitor_idx is not None else None
        competitor_score = float(match_matrix[competitor_idx][best_vacancy_idx]) if competitor_idx is not None else 0.0

        vacancy = vacancies[best_vacancy_idx]
        reason = _build_rejection_reason(candidate, competitor, best_score, competitor_score, vacancy)

        reserve.append({
            "candidate_id": candidate.id,
            "display_name": candidate.display_name,
            "best_vacancy_id": vacancy.id,
            "best_vacancy_title": vacancy.title,
            "best_score": round(best_score, 3),
            "competitor_candidate_id": competitor.id if competitor else None,
            "rejection_reason": reason,
            "rank": 0,
        })

    reserve = sorted(reserve, key=lambda x: -x["best_score"])
    for i, item in enumerate(reserve):
        item["rank"] = i + 1

    return {"reserve": reserve}


def _build_rejection_reason(candidate, competitor, score: float, competitor_score: float, vacancy) -> str:
    if competitor is None:
        return "Вакансия не могла быть закрыта в рамках ФОТ-лимита"

    if competitor_score > score:
        delta = round((competitor_score - score) * 100)
        return f"{competitor.display_name} подходит лучше на {delta}%"

    if (
        candidate.salary_expectation
        and vacancy.salary_max
        and candidate.salary_expectation > vacancy.salary_max
    ):
        over = int(candidate.salary_expectation - vacancy.salary_max)
        return f"Зарплатные ожидания превышают лимит вакансии на {over:,} ₽".replace(",", " ")

    return "Другой кандидат обеспечивает лучший баланс скиллов и стоимости"
