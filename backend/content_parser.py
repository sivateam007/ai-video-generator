"""Parse uploaded HTML and extract structured content for slides."""
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field
import re

@dataclass
class SlideSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    sub_sections: list = field(default_factory=list)

@dataclass
class ParsedContent:
    title: str
    hero_title: str = ""
    hero_subtitle: str = ""
    sections: list[SlideSection] = field(default_factory=list)

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_boilerplate(tag: Tag) -> bool:
    """Check if an element is navigational boilerplate."""
    if not isinstance(tag, Tag):
        return False
    # Tags to skip entirely
    skip_tags = {'script', 'style', 'nav', 'footer', 'header'}
    if tag.name in skip_tags:
        return True
    # Elements with boilerplate classes
    classes = tag.get('class', []) or []
    bp_classes = {'nav-tabs', 'bottom-nav', 'home-icon', 'nav', 'footer', 'header'}
    if any(c in bp_classes for c in classes):
        return True
    # Header parent
    if tag.name == 'header':
        return True
    return False

def is_content_container(tag: Tag) -> bool:
    """Check if a tag is a known content container."""
    classes = tag.get('class', []) or []
    content_classes = {'content-section', 'hero-content', 'section', 'main-content', 'tip-box', 'warning-box', 'exercise-box'}
    return any(c in content_classes for c in classes)

def extract_code_from_element(el: Tag) -> str | None:
    """Try to extract code from various code container patterns."""
    # Direct <pre><code>
    pre = el if el.name == 'pre' else None
    if pre is None:
        pre = el.find('pre')
    if pre:
        code_tag = pre.find('code')
        if code_tag:
            code = code_tag.get_text()
        else:
            code = pre.get_text()
        code_lines = [l for l in code.split('\n') if l.strip()]
        if code_lines:
            return '\n'.join(code_lines)
    return None

def parse_section_content(parent: Tag, section: SlideSection):
    """Parse children of a content container into the section."""
    for el in parent.children:
        if not isinstance(el, Tag):
            continue
        if is_boilerplate(el):
            continue
        tag = el.name

        if tag in ('h1', 'h2', 'h3', 'h4'):
            text = clean_text(el.get_text())
            if text:
                sub = SlideSection(heading=text)
                section.sub_sections.append(sub)
                parse_section_content(el, sub)

        elif tag == 'p':
            text = clean_text(el.get_text())
            if text and len(text) > 5:
                section.paragraphs.append(text)

        elif tag in ('ul', 'ol'):
            items = [clean_text(li.get_text()) for li in el.find_all('li') if clean_text(li.get_text())]
            section.list_items.extend(items)

        elif tag == 'pre':
            code = extract_code_from_element(el)
            if code:
                section.code_blocks.append(code)

        elif tag == 'div' and any(c in (el.get('class', []) or []) for c in ('code-example', 'code-block')):
            # Extract the heading/title of the code example
            h3 = el.find('h3')
            if h3:
                section.paragraphs.append(f"குறியீடு: {clean_text(h3.get_text())}")
            code = extract_code_from_element(el)
            if code:
                section.code_blocks.append(code)

        elif tag == 'div' and any(c in (el.get('class', []) or []) for c in ('tip-box', 'warning-box', 'exercise-box')):
            box_cls = [c for c in (el.get('class', []) or []) if c in ('tip-box', 'warning-box', 'exercise-box')][0]
            prefix = {'tip-box': 'TIP:', 'warning-box': 'WARNING:', 'exercise-box': 'EXERCISE:'}[box_cls]
            # Extract heading first
            h4 = el.find('h4')
            heading_text = clean_text(h4.get_text()) if h4 else ""
            # Extract all paragraphs inside
            inner_ps = [clean_text(p.get_text()) for p in el.find_all('p') if clean_text(p.get_text())]
            inner_lis = [clean_text(li.get_text()) for li in el.find_all('li') if clean_text(li.get_text())]
            all_text = heading_text + " " + " ".join(inner_ps) + " " + " ".join(inner_lis)
            text = clean_text(all_text)
            if text:
                section.paragraphs.append(f"{prefix} {text}")
            # Also extract list items and code inside
            parse_section_content(el, section)

        elif tag == 'img':
            alt = el.get('alt', '')
            src = el.get('src', '')
            if alt:
                section.paragraphs.append(f"[Image: {alt}]")

        elif tag == 'div':
            # Recurse into generic divs
            parse_section_content(el, section)

def parse_html(html_content: str) -> ParsedContent:
    soup = BeautifulSoup(html_content, 'html.parser')

    # Title
    title_tag = soup.find('title')
    title = clean_text(title_tag.get_text()) if title_tag else "Untitled Document"

    # Remove boilerplate elements
    for bp in soup.find_all(is_boilerplate):
        bp.decompose()

    for selector in ['nav', 'header', 'footer', '.nav-tabs', '.bottom-nav', '.home-icon', 'script', 'style']:
        for el in soup.select(selector):
            el.decompose()

    parsed = ParsedContent(title=title)

    # Hero section — include as first section
    hero = soup.select_one('.hero-content')
    if hero:
        h2 = hero.find('h2')
        p = hero.find('p')
        if h2:
            parsed.hero_title = clean_text(h2.get_text())
        if p:
            parsed.hero_subtitle = clean_text(p.get_text())
        # Add hero as first section
        hero_heading = clean_text(h2.get_text()) if h2 else "அறிமுகம்"
        hero_sec = SlideSection(heading=hero_heading)
        if p:
            hero_sec.paragraphs.append(clean_text(p.get_text()))
        if hero_sec.paragraphs:
            parsed.sections.insert(0, hero_sec)

    # Find main content area
    main = soup.select_one('main.container') or soup.select_one('main') or soup.select_one('.container') or soup.find('body')
    if not main:
        main = soup

    # Process content sections
    content_sections = main.find_all(['section', 'div'], class_=lambda c: c and any(
        cls in (c if isinstance(c, str) else c) for cls in ['content-section', 'section']
    ))

    if not content_sections:
        # Fallback: find all major headings in main
        content_sections = []
        current_section_tag = None
        for el in main.find_all(['h2', 'h3', 'section', 'div']):
            if el.name == 'h2':
                content_sections.append(el)
                current_section_tag = el
            elif el.name == 'h3' and current_section_tag:
                content_sections.append(el)

    for section_el in content_sections:
        # Get heading
        heading_tag = section_el.find(['h2', 'h3', 'h4']) if not section_el.name.startswith('h') else section_el
        heading = clean_text(heading_tag.get_text()) if heading_tag else ""

        if not heading:
            continue

        sec = SlideSection(heading=heading)
        parse_section_content(section_el, sec)

        # Flatten sub_sections if any
        if sec.sub_sections:
            for sub in sec.sub_sections:
                if sub.paragraphs or sub.code_blocks or sub.list_items:
                    sec.paragraphs.extend(sub.paragraphs)
                    sec.code_blocks.extend(sub.code_blocks)
                    sec.list_items.extend(sub.list_items)
            sec.sub_sections = []

        if sec.paragraphs or sec.code_blocks or sec.list_items:
            parsed.sections.append(sec)

    # If still no sections, extract all text
    if not parsed.sections:
        body = soup.find('body') or soup
        for tag in ['h2', 'h3', 'h4']:
            for h in body.find_all(tag):
                text = clean_text(h.get_text())
                if text:
                    sec = SlideSection(heading=text)
                    # Get all p/ul/pre until next heading
                    for sibling in h.find_next_siblings():
                        if sibling.name in ('h2', 'h3', 'h4'):
                            break
                        if sibling.name == 'p':
                            t = clean_text(sibling.get_text())
                            if t: sec.paragraphs.append(t)
                        elif sibling.name in ('ul', 'ol'):
                            items = [clean_text(li.get_text()) for li in sibling.find_all('li') if clean_text(li.get_text())]
                            sec.list_items.extend(items)
                        elif sibling.name == 'pre':
                            code = extract_code_from_element(sibling)
                            if code: sec.code_blocks.append(code)
                    if sec.paragraphs or sec.code_blocks or sec.list_items:
                        parsed.sections.append(sec)

    return parsed

# Test with sample HTML
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as f:
            html = f.read()
        p = parse_html(html)
        print(f"Title: {p.title}")
        print(f"Hero: {p.hero_title} — {p.hero_subtitle}")
        print(f"Sections: {len(p.sections)}")
        for s in p.sections:
            print(f"  [{s.heading}]")
            for par in s.paragraphs:
                print(f"    P: {par[:80]}...")
            for code in s.code_blocks:
                print(f"    CODE: {code[:60]}...")
            for li in s.list_items:
                print(f"    LI: {li[:60]}...")
