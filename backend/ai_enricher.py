"""Enrich parsed HTML content into structured slides with Tamil narration using Gemini."""
import json, os
from google import genai
from content_parser import ParsedContent, SlideSection

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SLIDE_PROMPT = """You are a Tamil educational video creator. Given HTML content about a programming/tech topic, create structured slides for a video.

The content has a main title and sections. For each section, create ONE slide with:

1. `title`: A short Tamil title (2-6 words)
2. `subtitle`: A brief Tamil subtitle/description (1 line)
3. `bullets`: 3-5 bullet points in Tamil explaining key concepts
4. `code`: A code example if relevant, otherwise empty string
5. `narration`: A 2-4 sentence Tamil narration script for voiceover. Explain the concept clearly and conversationally.

Rules:
- All Tamil text must be in Tamil script (not transliterated English)
- Code should remain in English (JavaScript)
- Make explanations beginner-friendly
- Keep narration conversational and clear

Return ONLY valid JSON. Format:
{
  "slides": [
    {
      "title": "தமிழ் தலைப்பு",
      "subtitle": "தமிழ் விளக்கம்",
      "bullets": ["புள்ளி 1", "புள்ளி 2", "புள்ளி 3"],
      "code": "console.log('hello');",
      "narration": "தமிழ் விளக்கம்..."
    }
  ]
}

For the first slide (title slide), create a welcome slide:
{
  "title": "வரவேற்பு",
  "subtitle": "முழுமையான தமிழ் கையேடு",
  "bullets": ["JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி"],
  "code": "",
  "narration": "வணக்கம், இந்த பாடத்தில்..."
}

Content to process:"""

def enrich_content(parsed: ParsedContent) -> list[dict]:
    if not GEMINI_API_KEY:
        return _fallback_slides(parsed)

    client = genai.Client(api_key=GEMINI_API_KEY)

    content_text = f"Title: {parsed.title}\n\n"
    for i, sec in enumerate(parsed.sections, 1):
        content_text += f"Section {i}: {sec.heading}\n"
        for p in sec.paragraphs:
            content_text += f"  {p}\n"
        for item in sec.list_items:
            content_text += f"  - {item}\n"
        for code in sec.code_blocks:
            content_text += f"  Code:\n{code}\n"
        content_text += "\n"

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[SLIDE_PROMPT + content_text],
            config={
                'response_mime_type': 'application/json',
            }
        )
        data = json.loads(response.text)
        slides = data.get('slides', [])
        if slides:
            return slides
    except Exception as e:
        print(f"AI enrichment failed: {e}")

    return _fallback_slides(parsed)

def _fallback_slides(parsed: ParsedContent) -> list[dict]:
    slides = [{
        "title": "வரவேற்பு",
        "subtitle": parsed.title,
        "bullets": ["JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி"],
        "code": "",
        "narration": f"வணக்கம், {parsed.title} பற்றிய இந்த பாடத்திற்கு அனைவருக்கும் வரவேற்பு."
    }]

    for sec in parsed.sections:
        if not sec.paragraphs and not sec.list_items and not sec.code_blocks:
            continue
        bullets = sec.list_items[:5] if sec.list_items else sec.paragraphs[:5]
        code = sec.code_blocks[0] if sec.code_blocks else ""
        narration = sec.paragraphs[0] if sec.paragraphs else f"{sec.heading} பற்றி இப்பகுதியில் காண்போம்."
        slides.append({
            "title": sec.heading[:30],
            "subtitle": f"{parsed.title} - முழுமையான விளக்கம்",
            "bullets": bullets,
            "code": code,
            "narration": narration
        })

    slides.append({
        "title": "சுருக்கம்",
        "subtitle": "முக்கிய கருத்துக்கள்",
        "bullets": [f"{parsed.title} பற்றி இப்பாடத்தில் கற்றுக் கொண்டோம்.",
                     "மேலும் தமிழில் நிரலாக்க கல்விக்கு JT Group of Institution-ஐ பின்தொடருங்கள்."],
        "code": "",
        "narration": f"இப்பாடத்தில் {parsed.title} பற்றி கற்றுக் கொண்டோம். கற்றலுக்கு நன்றி. வணக்கம்."
    })

    return slides

def generate_title_slide_overall(title: str) -> dict:
    return {
        "title": "வரவேற்பு",
        "subtitle": title,
        "bullets": ["JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி"],
        "code": "",
        "narration": f"JT Group of Institution சார்பாக {title} பற்றிய இந்த பாடத்திற்கு அனைவருக்கும் வரவேற்பு."
    }
