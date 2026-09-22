def compute_skill_gap(candidates: list, vacancies: list, assignment: dict) -> dict:
    """
    assignment: {str(vac_id): candidate_id or None} from OptimizationResult.assignment
    """
    required_skills: dict[str, int] = {}
    for vacancy in vacancies:
        for skill in (vacancy.required_skills or []):
            key = skill.lower()
            required_skills[key] = required_skills.get(key, 0) + 1

    cand_by_id = {c.id: c for c in candidates}

    covered_skills: dict[str, int] = {}
    for cand_id in assignment.values():
        if cand_id is None:
            continue
        candidate = cand_by_id.get(cand_id)
        if not candidate or not candidate.parsed_skills:
            continue
        for skill in candidate.parsed_skills.get("skills", []):
            key = skill.lower()
            covered_skills[key] = covered_skills.get(key, 0) + 1

    gaps = []
    fully_covered = []

    for skill, required_count in required_skills.items():
        covered_count = covered_skills.get(skill, 0)
        coverage = min(covered_count / required_count, 1.0) if required_count > 0 else 1.0
        if coverage >= 1.0:
            fully_covered.append(skill)
        else:
            gaps.append({
                "skill": skill,
                "coverage": round(coverage, 3),
                "required": required_count,
                "covered": covered_count,
                "critical": coverage == 0.0,
            })

    gaps = sorted(gaps, key=lambda x: x["coverage"])
    total_skills = len(required_skills)
    overall_coverage = len(fully_covered) / total_skills if total_skills > 0 else 0.0

    return {
        "gaps": gaps,
        "fully_covered": fully_covered,
        "overall_coverage": round(overall_coverage, 3),
    }
