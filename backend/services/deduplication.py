from sqlalchemy.orm import Session

from models.models import Candidate


class CandidateDeduplicator:
    SIMILARITY_THRESHOLD = 0.85

    def find_duplicates(
        self,
        new_candidate: Candidate,
        existing_candidates: list,
    ) -> list[dict]:
        if not existing_candidates:
            return []

        new_skills = set(
            s.lower()
            for s in (new_candidate.parsed_skills or {}).get("skills", [])
        )

        # Быстрый фильтр по Jaccard similarity скиллов
        skill_candidates = []
        for c in existing_candidates:
            if c.id == new_candidate.id:
                continue
            existing_skills = set(
                s.lower()
                for s in (c.parsed_skills or {}).get("skills", [])
            )
            if new_skills and existing_skills:
                union = new_skills | existing_skills
                if union:
                    jaccard = len(new_skills & existing_skills) / len(union)
                    if jaccard > 0.5:
                        skill_candidates.append(c)
            elif not new_skills and not existing_skills:
                skill_candidates.append(c)

        if not skill_candidates:
            return []

        # Точное сравнение по тексту через TF-IDF
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            texts = [new_candidate.raw_text_anonymized or ""] + [
                c.raw_text_anonymized or "" for c in skill_candidates
            ]
            if all(not t.strip() for t in texts):
                return []

            vectorizer = TfidfVectorizer(max_features=500)
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

            duplicates = []
            for i, sim in enumerate(similarities[0]):
                if sim >= self.SIMILARITY_THRESHOLD:
                    duplicates.append({
                        "candidate_id": skill_candidates[i].id,
                        "display_name": skill_candidates[i].display_name,
                        "similarity": round(float(sim), 3),
                        "is_likely_duplicate": sim >= 0.95,
                    })
            return sorted(duplicates, key=lambda x: -x["similarity"])

        except ImportError:
            # scikit-learn не установлен — возвращаем кандидатов из skill фильтра как potential duplicates
            return [
                {
                    "candidate_id": c.id,
                    "display_name": c.display_name,
                    "similarity": 0.6,
                    "is_likely_duplicate": False,
                }
                for c in skill_candidates[:5]
            ]

    def merge_candidates(self, primary_id: int, duplicate_id: int, db: Session) -> dict:
        primary = db.query(Candidate).filter(Candidate.id == primary_id).first()
        duplicate = db.query(Candidate).filter(Candidate.id == duplicate_id).first()
        if not primary or not duplicate:
            raise ValueError("Кандидат не найден")

        primary_skills = set((primary.parsed_skills or {}).get("skills", []))
        dup_skills = set((duplicate.parsed_skills or {}).get("skills", []))
        merged_skills = list(primary_skills | dup_skills)

        skills_data = dict(primary.parsed_skills or {})
        skills_data["skills"] = merged_skills
        primary.parsed_skills = skills_data

        if duplicate.salary_expectation and primary.salary_expectation:
            primary.salary_expectation = min(primary.salary_expectation, duplicate.salary_expectation)
        elif duplicate.salary_expectation:
            primary.salary_expectation = duplicate.salary_expectation

        duplicate.workflow_status = "merged"
        duplicate.merged_into = primary_id

        db.commit()
        return {"status": "merged", "primary_id": primary_id, "duplicate_id": duplicate_id}


deduplicator = CandidateDeduplicator()
