import re
from collections import Counter


def tokenize_query(query: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", query.lower())


def calculate_relevance(query_terms: list[str], title: str, abstract: str) -> float:
    title_terms = Counter(tokenize_query(title or ""))
    abstract_terms = Counter(tokenize_query(abstract or ""))
    score = 0
    for term in query_terms:
        score += title_terms[term] * 3
        score += abstract_terms[term]
    return score


def rank_papers(query: str, papers: list[dict]) -> list[dict]:
    query_terms = tokenize_query(query)
    if not query_terms:
        return []
    results = []
    for paper in papers:
        score = calculate_relevance(
            query_terms,
            paper.get("cleaned_title", ""),
            paper.get("cleaned_abstract", ""),
        )
        if score > 0:
            results.append({**paper, "relevance_score": score})
    return sorted(results, key=lambda paper: paper["relevance_score"], reverse=True)
