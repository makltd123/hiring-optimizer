import numpy as np


def compute_match_score(candidate_skills: list, required_skills: list) -> float:
    if not required_skills:
        return 0.0
    candidate_lower = [s.lower() for s in candidate_skills]
    matched = sum(
        1 for req in required_skills
        if any(req.lower() in c or c in req.lower() for c in candidate_lower)
    )
    return matched / len(required_skills)


def compute_weighted_score(candidate, vacancy, weights) -> float:
    skills = candidate.parsed_skills.get("skills", []) if candidate.parsed_skills else []
    skill_score = compute_match_score(skills, vacancy.required_skills or [])

    if candidate.salary_expectation and vacancy.salary_max and candidate.salary_expectation > 0:
        salary_score = min(vacancy.salary_max / candidate.salary_expectation, 1.0)
    else:
        salary_score = 0.5

    exp_years = (candidate.parsed_skills.get("experience_years", 0) or 0) if candidate.parsed_skills else 0
    exp_score = min(exp_years / 10, 1.0)

    total = weights.skill_match + weights.salary_fit + weights.experience
    if total == 0:
        return skill_score
    return (weights.skill_match * skill_score + weights.salary_fit * salary_score + weights.experience * exp_score) / total


def build_match_matrix(candidates: list, vacancies: list, weights=None) -> np.ndarray:
    matrix = np.zeros((len(candidates), len(vacancies)))
    for i, candidate in enumerate(candidates):
        skills = candidate.parsed_skills.get("skills", []) if candidate.parsed_skills else []
        for j, vacancy in enumerate(vacancies):
            if weights is not None:
                matrix[i][j] = compute_weighted_score(candidate, vacancy, weights)
            else:
                matrix[i][j] = compute_match_score(skills, vacancy.required_skills or [])
    return matrix
