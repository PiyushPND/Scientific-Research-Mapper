def generate_topic_label(keywords: list[dict]) -> str:
    if not keywords:
        return "Unclassified Research"
    terms = [item["keyword"] for item in keywords[:3]]
    label = "/".join(term.title() for term in terms)
    return label
