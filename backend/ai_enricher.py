"""Enrich parsed HTML content into structured slides with Tamil narration using Gemini."""
import json, os
from google import genai
from content_parser import ParsedContent, SlideSection

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SLIDE_PROMPT = """You are a Tamil educational video creator. Given HTML content about a programming/tech topic, create detailed, comprehensive structured slides for a video.

CRITICAL: Each slide's narration MUST be 30 to 60 SECONDS long when spoken aloud in Tamil. That is roughly 12-20 full sentences or 80-150 words per narration.

The content has a main title and sections. Create slides as follows:

FIRST SLIDE — Welcome slide:
  title: "வரவேற்பு"
  subtitle: The topic title in Tamil
  bullets: ["JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி", ... (2-3 welcome points)]
  code: ""
  narration: A warm 30-60 second welcome in Tamil introducing JT Group of Institution and the topic

For each section, create ONE detailed slide with:
1. `title`: A clear Tamil title (3-8 words)
2. `subtitle`: A descriptive Tamil subtitle (1-2 lines)
3. `bullets`: 4-6 detailed bullet points in Tamil. Each bullet = a complete sentence (10-20 words) teaching something specific
4. `code`: A relevant code example if section has code, otherwise ""
5. `narration`: LONG 30-60 second Tamil narration (12-20 sentences, 80-150 words). Explain conversationally, with real-world examples, step-by-step. Pretend teaching a beginner student face-to-face.

LAST SLIDE — Ending/Thanks slide:
  title: "நன்றி"
  subtitle: "JT Group of Institution"
  bullets: ["இப்பாடத்தில் கற்ற முக்கிய கருத்துக்களை மீள்பார்வை செய்யவும்", "தொடர்ந்து கற்றுக்கொள்ள எங்களை பின்தொடருங்கள்", "JT Group of Institution — தமிழில் கல்வி அனைவருக்கும்"]
  code: ""
  narration: A 30-60 second Tamil thanks message wrapping up what was learned, thanking the viewer, and inviting them to follow JT Group of Institution

Rules:
- All Tamil text must be in Tamil script (not transliterated English)
- Code in English (JavaScript/HTML/CSS)
- NARRATION MUST BE 30-60 SECONDS PER SLIDE — at least 12-20 full sentences
- Conversational, clear, beginner-friendly teaching style
- Practical examples and real-world applications in bullets and narration
- Include welcome as first slide and thanks as last slide

Return ONLY valid JSON. Format:
{
  "slides": [
    {
      "title": "தமிழ் தலைப்பு",
      "subtitle": "தமிழ் விளக்கம்",
      "bullets": ["விளக்கம் 1", "விளக்கம் 2", "விளக்கம் 3"],
      "code": "console.log('hello');",
      "narration": "தமிழ் விளக்கம்..."
    }
  ]
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
        "bullets": [
            "JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி",
            f"{parsed.title} பற்றி முழுமையான விளக்கம்",
            "எளிய முறையில் புரிந்துகொள்ளும் விளக்கங்கள்"
        ],
        "code": "",
        "narration": f"வணக்கம், JT Group of Institution சார்பாக {parsed.title} பற்றிய இந்த பாடத்திற்கு அனைவருக்கும் வரவேற்பு. இந்த பாடத்தில் முக்கிய கருத்துக்களை எளிய முறையில் காண்போம். JT Group of Institution எப்போதும் தமிழில் தரமான கல்வியை வழங்க உறுதிபூண்டுள்ளது. இந்த பாடம் முழுவதும் நம்முடன் இருங்கள். பாடத்தின் முடிவில் நீங்கள் நிறைய புதிய விஷயங்களை கற்றுக் கொள்வீர்கள். ஆரம்பிக்கலாமா?"
    }]

    for sec in parsed.sections:
        if not sec.paragraphs and not sec.list_items and not sec.code_blocks:
            continue
        bullets = (sec.list_items[:5] if sec.list_items else sec.paragraphs[:5])
        code = sec.code_blocks[0] if sec.code_blocks else ""
        narration_parts = [p for p in sec.paragraphs[:6] if p]
        if narration_parts:
            narration = " ".join(narration_parts)
        else:
            narration = f"{sec.heading} பற்றி இப்பகுதியில் விரிவாக காண்போம். இது ஒரு முக்கியமான தலைப்பு ஆகும். இதை புரிந்து கொள்வதன் மூலம் நிரலாக்கத்தில் உங்கள் திறன் அதிகரிக்கும். நிஜ உலக உதாரணங்களுடன் இதை விளக்குகிறோம். தொடர்ந்து கவனியுங்கள்."
        slides.append({
            "title": sec.heading[:40],
            "subtitle": f"{parsed.title} - {sec.heading[:30]}",
            "bullets": bullets,
            "code": code,
            "narration": narration
        })

    slides.append({
        "title": "நன்றி",
        "subtitle": "JT Group of Institution",
        "bullets": [
            f"{parsed.title} பற்றி இப்பாடத்தில் விரிவாக கற்றுக் கொண்டோம்.",
            "மேலும் தமிழில் நிரலாக்க கல்விக்கு JT Group of Institution-ஐ பின்தொடருங்கள்.",
            "தொடர்ந்து கற்றுக்கொள்ள எங்கள் பக்கத்தை பின்தொடரவும்."
        ],
        "code": "",
        "narration": f"இப்பாடத்தில் {parsed.title} பற்றி முழுமையாக கற்றுக் கொண்டோம். இன்று நாம் கற்ற அனைத்து கருத்துக்களையும் மீள்பார்வை செய்யுங்கள். தொடர்ந்து பயிற்சி செய்வதன் மூலம் உங்கள் திறமையை மேம்படுத்தலாம். JT Group of Institution வழங்கும் இத்தகைய கல்வி பயனுள்ளதாக இருந்தால் எங்களை பின்தொடருங்கள். மேலும் பல பாடங்களை தமிழில் கற்றுக்கொள்ளுங்கள். கற்றலுக்கு நன்றி. அனைவருக்கும் வணக்கம்."
    })

    return slides

def generate_title_slide_overall(title: str) -> dict:
    return {
        "title": "வரவேற்பு",
        "subtitle": title,
        "bullets": ["JT Group of Institution வழங்கும் தமிழ் நிரலாக்க கல்வி"],
        "code": "",
        "narration": f"JT Group of Institution சார்பாக {title} பற்றிய இந்த பாடத்திற்கு அனைவருக்கும் வரவேற்பு. தமிழில் நிரலாக்க கல்வியை எளிய முறையில் கற்றுக் கொள்ள இங்கு வந்தமைக்கு நன்றி."
    }
