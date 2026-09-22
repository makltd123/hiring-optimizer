import re


def anonymize(text: str) -> str:
    text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)
    text = re.sub(
        r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        '[PHONE]',
        text,
    )
    lines = text.strip().split('\n')
    if lines and len(lines[0].split()) <= 4 and lines[0].strip() and lines[0].strip()[0].isupper():
        lines[0] = '[ИМЯ УДАЛЕНО]'
    return '\n'.join(lines)
