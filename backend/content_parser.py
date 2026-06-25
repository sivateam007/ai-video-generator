"""Parse uploaded HTML and extract structured content for slides."""
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
import re

@dataclass
class SlideSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)

@dataclass
class ParsedContent:
    title: str
    sections: list[SlideSection] = field(default_factory=list)

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_html(html_content: str) -> ParsedContent:
    soup = BeautifulSoup(html_content, 'html.parser')

    title_tag = soup.find('title')
    title = clean_text(title_tag.get_text()) if title_tag else "Untitled Document"

    main_h1 = soup.find('h1')
    main_title = clean_text(main_h1.get_text()) if main_h1 else title

    parsed = ParsedContent(title=main_title)
    current_section = None

    for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'pre', 'ul', 'ol', 'code']):
        # Skip the main h1 (it's the title)
        if el.name == 'h1' and el == main_h1:
            continue
        if el.name in ('h1', 'h2', 'h3', 'h4'):
            if current_section:
                parsed.sections.append(current_section)
            current_section = SlideSection(heading=clean_text(el.get_text()))
        elif current_section:
            if el.name == 'p':
                text = clean_text(el.get_text())
                if text:
                    current_section.paragraphs.append(text)
            elif el.name == 'pre':
                code = el.get_text()
                code_lines = [l for l in code.split('\n') if l.strip()]
                if code_lines:
                    current_section.code_blocks.append('\n'.join(code_lines))
            elif el.name == 'code' and el.parent.name != 'pre':
                code = clean_text(el.get_text())
                if code:
                    current_section.code_blocks.append(code)
            elif el.name in ('ul', 'ol'):
                items = [clean_text(li.get_text()) for li in el.find_all('li')]
                current_section.list_items.extend(items)

    if current_section:
        parsed.sections.append(current_section)

    if not parsed.sections:
        body = soup.find('body') or soup
        text = clean_text(body.get_text())
        if text:
            parsed.sections.append(SlideSection(
                heading=parsed.title,
                paragraphs=[text[:500]]
            ))

    return parsed
