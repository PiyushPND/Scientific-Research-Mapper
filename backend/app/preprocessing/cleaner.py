import hashlib
import re
import unicodedata
from html.parser import HTMLParser

PREPROCESSING_VERSION = "1.0"


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style"}:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def remove_html(text):
    parser = HTMLTextExtractor()
    try:
        parser.feed(text)
        parser.close()
        return parser.get_text()
    except Exception:
        raise ValueError("Unable to parse HTML content.")


def clean_text(text):
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = remove_html(text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text, flags=re.IGNORECASE)
    text = "".join(
        character
        for character in text
        if unicodedata.category(character) not in {"Cc", "Cf"} or character in "\n\t"
    )
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_source_hash(title, abstract):
    source = title + "\0" + abstract + "\0" + PREPROCESSING_VERSION
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def preprocess_paper(paper):
    original_title = paper["title"]
    original_abstract = paper["abstract"]
    cleaned_title = clean_text(original_title)
    cleaned_abstract = clean_text(original_abstract)
    if not cleaned_title:
        raise ValueError("Title became empty after preprocessing.")
    if not cleaned_abstract:
        raise ValueError("Abstract became empty after preprocessing.")
    combined_text = cleaned_title + ". " + cleaned_abstract
    source_hash = create_source_hash(original_title, original_abstract)
    return {
        "paper_id": paper["paper_id"],
        "cleaned_title": cleaned_title,
        "cleaned_abstract": cleaned_abstract,
        "combined_text": combined_text,
        "source_hash": source_hash,
        "preprocessing_version": PREPROCESSING_VERSION,
    }
