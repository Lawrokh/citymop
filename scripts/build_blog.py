#!/usr/bin/env python3
"""
=====================================================================
CityMop — automatyczny generator postów blogowych
=====================================================================
Uruchamiany przez GitHub Actions raz dziennie.
Wykorzystuje Claude API + plik wiedzy SEO (RAG) jako kontekst,
aby generować artykuły zgodne z najlepszymi praktykami SEO/GEO/LLM:
  - BLUF (Bottom Line Up Front) w pierwszych 50 słowach
  - Atomic Claims (twierdzenia weryfikowalne, z liczbami)
  - Autonomiczność chunków pod H2 (samodzielnie zrozumiałe)
  - Central Entity = "CityMop" jako Agent (strona czynna)
  - JSON-LD: Article + HowTo + FAQPage
  - E-E-A-T: autor, organizacja, doświadczenie

Generuje pełen plik HTML w blog/<slug>/index.html, aktualizuje
listę bloga (blog/index.html), sitemap.xml oraz feed RSS.
=====================================================================
"""

from __future__ import annotations

import json
import os
import re
import sys
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Wymaga: pip install anthropic
from anthropic import Anthropic


# =====================================================================
# KONFIGURACJA
# =====================================================================

ROOT = Path(__file__).resolve().parent.parent  # katalog główny strony
BLOG_DIR = ROOT / "blog"
RAG_PATH = ROOT / "scripts" / "seo_encyklopedia_rag.jsonl"
TOPICS_PATH = ROOT / "scripts" / "topics_pool.json"
DOMAIN = "https://citymop.pl"

# Tematy posortowane wg priorytetu SEO (high-intent local + transactional)
# Jeśli pula się wyczerpie, skrypt zacznie generować z auto-podpowiedzi.
DEFAULT_TOPICS = [
    "Jak zorganizować generalne sprzątanie mieszkania w jeden weekend",
    "Czym myć podłogi drewniane, żeby nie zostawiać smug",
    "Jak usunąć plamy z dywanu — pełna lista metod według typu plamy",
    "Sprzątanie po zwierzętach — przewodnik dla właścicieli kotów i psów",
    "Jak prać dywan wełniany w domu i nie zniszczyć włosa",
    "Czyszczenie fug w łazience — domowe metody, które działają",
    "Pranie materaca — kiedy konieczne, kiedy wystarczy odkurzanie",
    "Sprzątanie biura — checklisty codzienne, tygodniowe i miesięczne",
    "Jak myć okna bez smug — sześć błędów, które wszyscy popełniają",
    "Czyszczenie piekarnika domowymi sposobami — soda, ocet, sól",
    "Czym pachnie czysty dom — chemia zapachów porządku",
    "Jak usunąć kamień z baterii i armatury bez agresywnej chemii",
    "Czy warto kupić robot sprzątający w 2026 — uczciwa analiza",
    "Sprzątanie po imprezie — instrukcja w 90 minut",
    "Jak czyścić lodówkę raz w miesiącu, żeby nigdy nie śmierdziała",
    "Czyszczenie pralki — drożdżaki, kamień i zapach gumy",
    "Sprzątanie kuchni — strefy, które najczęściej omijasz",
    "Jak prać firany i zasłony — temperatura, środki, suszenie",
    "Czyszczenie żaluzji i rolet — szybkie metody bez demontażu",
    "Sprzątanie po remoncie łazienki — kolejność czynności krok po kroku",
]

# Kategorie tematyczne (do post_meta i article:section)
CATEGORIES = {
    "kanape": "Pranie tapicerek",
    "tapicer": "Pranie tapicerek",
    "dywan": "Pranie dywanów",
    "remont": "Po remoncie",
    "biuro": "Sprzątanie biur",
    "mieszk": "Sprzątanie domów",
    "dom": "Sprzątanie domów",
    "okn": "Okna",
    "kuch": "Kuchnia",
    "łazien": "Łazienka",
    "pralk": "Pralka",
    "lodów": "Lodówka",
    "piekarni": "Kuchnia",
}


# =====================================================================
# UTILS
# =====================================================================

def slugify(text: str) -> str:
    """Polski-friendly slugify."""
    repl = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    text = text.translate(repl).lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


def category_for(title: str) -> str:
    # Normalizuj polskie znaki dla niezawodnego dopasowania
    repl = str.maketrans("ąćęłńóśźż", "acelnoszz")
    low = title.lower().translate(repl)
    # Lista posortowana — od najbardziej specyficznych do ogólnych
    ordered = [
        ("kanap", "Pranie tapicerek"),
        ("tapicer", "Pranie tapicerek"),
        ("sofa", "Pranie tapicerek"),
        ("fotel", "Pranie tapicerek"),
        ("material", "Pranie tapicerek"),
        ("dywan", "Pranie dywanów"),
        ("wykladzin", "Pranie dywanów"),
        ("remon", "Po remoncie"),
        ("biur", "Sprzątanie biur"),
        ("firm", "Sprzątanie biur"),
        ("mieszka", "Sprzątanie domów"),
        ("kawalerk", "Sprzątanie domów"),
        ("dom", "Sprzątanie domów"),
        ("okien", "Okna"),
        ("okna", "Okna"),
        ("okno", "Okna"),
        ("kuch", "Kuchnia"),
        ("lazien", "Łazienka"),
        ("pralk", "Pralka"),
        ("lodow", "Lodówka"),
        ("piekarni", "Kuchnia"),
        ("cennik", "Cennik"),
        ("ile kosztuje", "Cennik"),
        ("cena", "Cennik"),
    ]
    for key, cat in ordered:
        if key in low:
            return cat
    return "Porady"


def load_rag(limit: int = 60) -> str:
    """
    Wczytuje skróty z encyklopedii SEO. Limit, aby nie przekroczyć
    kontekstu — wybiera kluczowe wpisy z różnych kategorii.
    """
    if not RAG_PATH.exists():
        print(f"[WARN] RAG file not found at {RAG_PATH}", file=sys.stderr)
        return ""

    entries = []
    with open(RAG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Priorytetowe kategorie pod content writing
    priority = {
        "Mikrosemantyka (poziom passage)": 12,
        "AI Search": 10,
        "Fundamenty teoretyczne": 8,
        "E-E-A-T": 6,
        "Makrosemantyka (poziom witryny)": 6,
        "Pipeline'y audytu semantycznego": 6,
        "Metryki i audyt": 4,
        "Semantyka leksykalna": 4,
        "Grafy wiedzy": 4,
    }

    by_cat: dict[str, list] = {}
    for e in entries:
        cat = e.get("metadata", {}).get("category", "inne")
        by_cat.setdefault(cat, []).append(e)

    chosen = []
    for cat, n in priority.items():
        chosen.extend(by_cat.get(cat, [])[:n])

    chosen = chosen[:limit]

    # Skrócona wersja do kontekstu LLM
    summary = []
    for e in chosen:
        summary.append(f"### {e['title']}\n{e['short_description'][:400]}")

    return "\n\n".join(summary)


def existing_slugs() -> set[str]:
    """Zwraca slugi istniejących postów."""
    slugs = set()
    if BLOG_DIR.exists():
        for d in BLOG_DIR.iterdir():
            if d.is_dir() and (d / "index.html").exists():
                slugs.add(d.name)
    return slugs


def pick_topic() -> str:
    """Wybiera temat z puli — preferuje pulę z pliku, fallback na defaults."""
    pool = DEFAULT_TOPICS[:]
    if TOPICS_PATH.exists():
        try:
            extra = json.loads(TOPICS_PATH.read_text("utf-8"))
            if isinstance(extra, list):
                pool = extra + pool
        except json.JSONDecodeError:
            pass

    used = existing_slugs()
    available = [t for t in pool if slugify(t) not in used]

    if not available:
        # Generuj nowy temat przez Claude, jeśli baza wyczerpana
        return None
    return random.choice(available)


# =====================================================================
# CLAUDE API CALL
# =====================================================================

SYSTEM_PROMPT_TEMPLATE = """\
Jesteś senior content writerem i specjalistą SEO/GEO firmy CityMop —
firmy sprzątającej z Buska-Zdroju (woj. świętokrzyskie).

USŁUGI CityMop (Central Entity = CityMop, jako Agent w stronie czynnej):
  - sprzątanie domów i mieszkań prywatnych
  - sprzątanie biur i firm
  - sprzątanie po remoncie
  - pranie tapicerek, sof, foteli, kanap
  - pranie dywanów i wykładzin
Obszar: Busko-Zdrój i 30 km od centrum (Solec-Zdrój, Stopnica, Nowy Korczyn,
Wiślica, Pińczów, Chmielnik, Kazimierza Wielka, Pacanów).
Kontakt: +48 530 610 336, info@citymop.pl

OBOWIĄZUJĄCE ZASADY SEO/GEO/LLM (z encyklopedii semantycznego SEO):

{rag_context}

KRYTYCZNE WYTYCZNE PISARSKIE (NIE NEGOCJOWALNE):
1. **BLUF**: pierwszy paragraf zawiera bezpośrednią odpowiedź na tytuł
   w 40–55 słowach, z konkretnymi liczbami (czas, koszt, ilość).
2. **Atomic Claims**: każde twierdzenie musi być weryfikowalne.
   "Pranie zajmuje 60-90 min" – TAK. "Pranie jest szybkie" – NIE.
3. **Central Entity**: gdy padają usługi sprzątania, podmiotem zdania
   jest CityMop (strona czynna): "CityMop pierze kanapy", NIE
   "kanapy są prane".
4. **Autonomiczność chunków**: każdy paragraf pod H2 musi być
   zrozumiały samodzielnie, bez "jak wspomniano powyżej".
5. **E-E-A-T**: bądź konkretny, pokazuj doświadczenie ("w naszej praktyce",
   "u 8 z 10 klientów"), unikaj ogólników.
6. **Encje i atrybuty**: używaj konkretnych nazw środków, marek, metod,
   liczb, lokalizacji. NIGDY "różne metody", "wiele osób".
7. Polski język, zero anglicyzmów, zero buzzwords.

Liczba sections: 4-7. Liczba FAQ: 3-5. HowTo: 4-6 kroków (lub pusta tablica,
jeśli temat nie jest instruktażowy).

Wynik MUSISZ zwrócić wywołując narzędzie `save_blog_post` z polami wg schemy.
"""


# Schemat narzędzia (tool use) — gwarantuje poprawny, walidowany JSON.
SAVE_POST_TOOL = {
    "name": "save_blog_post",
    "description": (
        "Zapisuje strukturę gotowego artykułu blogowego CityMop. "
        "Wszystkie pola są obowiązkowe poza howto_steps i list w sekcjach."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Tytuł, max 70 znaków, ze słowem kluczowym."},
            "meta_description": {"type": "string", "description": "Opis 145–160 znaków, BLUF na początku."},
            "category": {"type": "string", "description": "np. 'Pranie tapicerek', 'Sprzątanie domów'"},
            "reading_time_min": {"type": "integer", "minimum": 2, "maximum": 15},
            "bluf_box": {"type": "string", "description": "Akapit BLUF: 40–55 słów, konkrety, liczby, CityMop jako agent."},
            "lead": {"type": "string", "description": "Lead pod H1, 2–3 zdania, max 40 słów."},
            "intro_paragraphs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
            },
            "sections": {
                "type": "array",
                "minItems": 4,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "h2": {"type": "string"},
                        "paragraphs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 6,
                        },
                    },
                    "required": ["h2", "paragraphs"],
                },
            },
            "faq": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "q": {"type": "string"},
                        "a": {"type": "string"},
                    },
                    "required": ["q", "a"],
                },
            },
            "howto_steps": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["name", "text"],
                },
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 10,
            },
        },
        "required": [
            "title", "meta_description", "category", "bluf_box",
            "lead", "intro_paragraphs", "sections", "faq", "keywords",
        ],
    },
}


def generate_post_via_claude(topic: str, rag_context: str) -> dict:
    """
    Wywołuje Claude API z wymuszonym tool use — gwarantuje poprawnie
    sformatowany JSON zgodny ze schemą (bez ryzyka błędów parsowania).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Brak zmiennej środowiskowej ANTHROPIC_API_KEY")

    client = Anthropic(api_key=api_key)
    system = SYSTEM_PROMPT_TEMPLATE.format(rag_context=rag_context)

    user_msg = (
        f"Napisz dzisiejszy artykuł blogowy na temat: \"{topic}\".\n\n"
        f"Optymalizuj pod AI Search (ChatGPT, Perplexity, Google AI Mode, Claude) "
        f"oraz pod tradycyjne SEO. Pamiętaj o lokalnych frazach z Buska-Zdroju.\n"
        f"Zwróć wynik wywołując narzędzie `save_blog_post`."
    )

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8000,
        system=system,
        tools=[SAVE_POST_TOOL],
        tool_choice={"type": "tool", "name": "save_blog_post"},
        messages=[{"role": "user", "content": user_msg}],
    )

    # Wyciągnij blok tool_use z odpowiedzi
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "save_blog_post":
            return block.input

    # Fallback: stary tryb (gdyby tool_use nie wrócił)
    text_blocks = [b for b in response.content if getattr(b, "type", None) == "text"]
    if text_blocks:
        raw = text_blocks[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    raise RuntimeError("Claude nie zwrócił ani tool_use, ani text — nieoczekiwana odpowiedź.")


# =====================================================================
# RENDER HTML
# =====================================================================

def render_post_html(data: dict, slug: str) -> str:
    """Generuje pełen plik HTML artykułu z poprawnym Schema.org."""

    title = data["title"]
    meta_desc = data["meta_description"]
    category = data.get("category", category_for(title))
    bluf = data["bluf_box"]
    lead = data["lead"]
    intro = data.get("intro_paragraphs", [])
    sections = data.get("sections", [])
    faq = data.get("faq", [])
    howto = data.get("howto_steps", [])
    keywords = data.get("keywords", [])
    reading_time = data.get("reading_time_min", 4)

    today = datetime.now(timezone(timedelta(hours=2)))
    iso_date = today.isoformat()
    display_date = today.strftime("%d.%m.%Y")
    url = f"{DOMAIN}/blog/{slug}/"

    # Sections HTML
    sections_html = []
    for s in sections:
        h2 = s.get("h2", "")
        parts = [f"<h2>{escape_html(h2)}</h2>"]
        for p in s.get("paragraphs", []):
            parts.append(f"<p>{escape_html(p)}</p>")
        lst = s.get("list", [])
        if lst:
            parts.append("<ul>")
            for li in lst:
                parts.append(f"  <li>{escape_html(li)}</li>")
            parts.append("</ul>")
        sections_html.append("\n    ".join(parts))
    sections_block = "\n\n    ".join(sections_html)

    # FAQ HTML + JSON-LD
    faq_html_parts = []
    if faq:
        faq_html_parts.append('<h2>Najczęstsze pytania</h2>')
        for item in faq:
            faq_html_parts.append(f"<h3>{escape_html(item['q'])}</h3>")
            faq_html_parts.append(f"<p>{escape_html(item['a'])}</p>")
    faq_block = "\n    ".join(faq_html_parts)

    faq_jsonld = ""
    if faq:
        faq_jsonld = ",\n" + json.dumps({
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": item["a"]}
                }
                for item in faq
            ]
        }, ensure_ascii=False, indent=2)

    # HowTo JSON-LD
    howto_jsonld = ""
    if howto:
        howto_jsonld = ",\n" + json.dumps({
            "@type": "HowTo",
            "name": title,
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": s["name"],
                    "text": s["text"]
                }
                for i, s in enumerate(howto)
            ]
        }, ensure_ascii=False, indent=2)

    intro_html = "\n    ".join(f"<p>{escape_html(p)}</p>" for p in intro)

    # Article JSON-LD
    article_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{url}#article",
                "headline": title,
                "description": meta_desc,
                "datePublished": iso_date,
                "dateModified": iso_date,
                "author": {"@type": "Organization", "name": "CityMop", "url": DOMAIN + "/"},
                "publisher": {
                    "@type": "Organization",
                    "name": "CityMop",
                    "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/assets/logo.png"}
                },
                "mainEntityOfPage": url,
                "inLanguage": "pl-PL",
                "articleSection": category,
                "keywords": ", ".join(keywords),
            }
        ]
    }, ensure_ascii=False, indent=2)

    # Wstaw FAQ i HowTo do @graph
    if faq_jsonld or howto_jsonld:
        article_jsonld = article_jsonld.replace(
            '"keywords": "' + ", ".join(keywords) + '"\n            }',
            '"keywords": "' + ", ".join(keywords) + '"\n            }'
            + faq_jsonld + howto_jsonld
        )

    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>{escape_html(title)} | CityMop</title>
<meta name="description" content="{escape_html(meta_desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="keywords" content="{escape_html(', '.join(keywords))}">

<meta property="og:type" content="article">
<meta property="og:title" content="{escape_html(title)}">
<meta property="og:description" content="{escape_html(meta_desc)}">
<meta property="og:url" content="{url}">
<meta property="article:published_time" content="{iso_date}">
<meta property="article:author" content="CityMop">
<meta property="article:section" content="{escape_html(category)}">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght,SOFT,WONK@0,9..144,300..700,30..100,0..1;1,9..144,300..700,30..100,0..1&family=Manrope:wght@300..700&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="/css/style.css">

<script type="application/ld+json">
{article_jsonld}
</script>
</head>
<body>

<header class="nav" role="banner">
  <div class="container nav-inner">
    <a href="/" class="brand">
      <img src="/assets/logo.png" alt="CityMop" class="brand-logo" width="180" height="56">
    </a>
    <nav aria-label="Główna nawigacja">
      <ul class="nav-links">
        <li><a href="/#uslugi">Usługi</a></li>
        <li><a href="/#proces">Jak pracujemy</a></li>
        <li><a href="/#obszar">Obszar</a></li>
        <li><a href="/blog/">Blog</a></li>
        <li><a href="/#faq">FAQ</a></li>
      </ul>
    </nav>
    <a href="/#kontakt" class="nav-cta">Zamów wycenę →</a>
    <button class="nav-toggle" aria-label="Menu"><span></span><span></span></button>
  </div>
</header>

<article>
  <header class="article-hero">
    <div class="container">
      <div class="article-meta">
        <span><a href="/blog/" style="color:inherit">← Blog</a></span>
        <span>{escape_html(category)}</span>
        <span>{display_date}</span>
        <span>{reading_time} min czytania</span>
      </div>
      <h1>{escape_html(title)}</h1>
      <p class="lead">{escape_html(lead)}</p>
      <div class="article-author">
        <div class="avatar">CM</div>
        <div>
          <div class="name">Zespół CityMop</div>
          <div class="role">Firma sprzątająca · Busko-Zdrój · 8 lat doświadczenia</div>
        </div>
      </div>
    </div>
  </header>

  <div class="article-body">

    <div class="bluf-box">
      <p><strong>W skrócie:</strong> {escape_html(bluf)}</p>
    </div>

    {intro_html}

    {sections_block}

    {faq_block}

    <hr style="margin: 3rem 0; border: none; border-top: 1px solid rgba(20,32,31,0.1);">

    <p style="background: var(--c-foam); padding: 1.5rem; border-radius: 1rem; text-align: center;">
      <strong>Potrzebujesz, żeby ktoś to zrobił za Ciebie?</strong><br>
      CityMop sprząta i pierze w Busku-Zdroju i okolicy.<br>
      <a href="/#kontakt" style="color: var(--c-zdroj); font-weight: 600;">Zamów bezpłatną wycenę →</a>
    </p>
  </div>
</article>

<footer class="footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="brand"><img src="/assets/logo.png" alt="CityMop" class="brand-logo" width="180" height="56"></div>
        <p class="footer-tagline">Firma sprzątająca z Buska-Zdroju.</p>
      </div>
      <div>
        <h4>Usługi</h4>
        <ul>
          <li><a href="/#uslugi">Sprzątanie domów</a></li>
          <li><a href="/#uslugi">Sprzątanie biur</a></li>
          <li><a href="/#uslugi">Po remoncie</a></li>
          <li><a href="/#uslugi">Pranie tapicerek</a></li>
        </ul>
      </div>
      <div>
        <h4>Firma</h4>
        <ul>
          <li><a href="/blog/">Blog</a></li>
          <li><a href="/#obszar">Obszar</a></li>
          <li><a href="/#faq">FAQ</a></li>
          <li><a href="/#kontakt">Kontakt</a></li>
        </ul>
      </div>
      <div>
        <h4>Kontakt</h4>
        <ul>
          <li><a href="tel:+48537480480">+48 530 610 336</a></li>
          <li><a href="mailto:info@citymop.pl">info@citymop.pl</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© <span id="year">{today.year}</span> CityMop. Wszystkie prawa zastrzeżone.</span>
    </div>
  </div>
</footer>

<script src="/js/main.js" defer></script>
</body>
</html>
"""


def escape_html(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# =====================================================================
# UPDATE BLOG INDEX, SITEMAP, RSS
# =====================================================================

def collect_all_posts() -> list[dict]:
    """Zwraca metadane wszystkich postów na potrzeby listy, sitemap, RSS."""
    posts = []
    if not BLOG_DIR.exists():
        return posts

    for d in sorted(BLOG_DIR.iterdir()):
        if not d.is_dir():
            continue
        idx = d / "index.html"
        if not idx.exists():
            continue
        html = idx.read_text("utf-8", errors="ignore")

        title_m = re.search(r"<title>([^<|]+)", html)
        desc_m = re.search(r'name="description" content="([^"]+)"', html)
        date_m = re.search(r'article:published_time" content="([^"]+)"', html)
        section_m = re.search(r'article:section" content="([^"]+)"', html)

        posts.append({
            "slug": d.name,
            "title": title_m.group(1).strip() if title_m else d.name,
            "description": desc_m.group(1) if desc_m else "",
            "date": date_m.group(1) if date_m else "2026-01-01T00:00:00+02:00",
            "category": section_m.group(1) if section_m else "Porady",
        })

    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def update_blog_index(posts: list[dict]):
    """Aktualizuje listę postów na blog/index.html."""
    idx_path = BLOG_DIR / "index.html"
    if not idx_path.exists():
        return

    cards = []
    for p in posts:
        date_str = p["date"][:10].split("-")
        try:
            display = f"{date_str[2]}.{date_str[1]}.{date_str[0]}"
        except (IndexError, ValueError):
            display = p["date"][:10]
        cards.append(f'''      <a href="/blog/{p["slug"]}/" class="post-card">
        <div class="post-meta">
          <span>{escape_html(p["category"])}</span>
          <span>{display}</span>
        </div>
        <h3>{escape_html(p["title"])}</h3>
        <p>{escape_html(p["description"][:160])}</p>
        <span class="read-more">Czytaj artykuł →</span>
      </a>''')

    cards_html = "\n\n".join(cards)
    html = idx_path.read_text("utf-8")
    new_html = re.sub(
        r'(<div class="blog-grid"[^>]*id="all-posts"[^>]*>).*?(</div>\s*</div>\s*</section>)',
        r'\1\n' + cards_html + '\n    \\2',
        html,
        flags=re.DOTALL,
    )
    idx_path.write_text(new_html, "utf-8")
    print(f"[OK] Updated blog index with {len(posts)} posts")


def generate_sitemap(posts: list[dict]):
    """Generuje sitemap.xml."""
    urls = [
        f"<url><loc>{DOMAIN}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>",
        f"<url><loc>{DOMAIN}/blog/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>",
    ]
    for p in posts:
        urls.append(
            f'<url><loc>{DOMAIN}/blog/{p["slug"]}/</loc>'
            f'<lastmod>{p["date"][:10]}</lastmod>'
            f'<changefreq>monthly</changefreq><priority>0.7</priority></url>'
        )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(sitemap, "utf-8")
    print(f"[OK] Generated sitemap.xml with {len(urls)} URLs")


def generate_rss(posts: list[dict]):
    """Generuje RSS feed dla bloga."""
    items = []
    for p in posts[:30]:
        items.append(f"""    <item>
      <title>{escape_html(p["title"])}</title>
      <link>{DOMAIN}/blog/{p["slug"]}/</link>
      <guid>{DOMAIN}/blog/{p["slug"]}/</guid>
      <description>{escape_html(p["description"])}</description>
      <category>{escape_html(p["category"])}</category>
      <pubDate>{p["date"]}</pubDate>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Blog CityMop — sprzątanie, pranie, porządek</title>
    <link>{DOMAIN}/blog/</link>
    <atom:link href="{DOMAIN}/blog/feed.xml" rel="self" type="application/rss+xml"/>
    <description>Codzienne porady firmy sprzątającej CityMop z Buska-Zdroju.</description>
    <language>pl-pl</language>
    <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (BLOG_DIR / "feed.xml").write_text(rss, "utf-8")
    print(f"[OK] Generated RSS feed with {len(items)} items")


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 60)
    print(f"CityMop daily post generator — {datetime.now().isoformat()}")
    print("=" * 60)

    # 1. Wybierz temat
    topic = pick_topic()
    if not topic:
        print("[INFO] Pula tematów wyczerpana. Dodaj nowe do scripts/topics_pool.json")
        sys.exit(0)
    print(f"[INFO] Wybrany temat: {topic}")

    slug = slugify(topic)
    target_dir = BLOG_DIR / slug
    if target_dir.exists():
        print(f"[INFO] Post {slug} już istnieje. Pomijam.")
        sys.exit(0)

    # 2. Wczytaj kontekst SEO/RAG
    print("[INFO] Wczytywanie wiedzy SEO z RAG…")
    rag_context = load_rag()

    # 3. Wygeneruj treść przez Claude
    print("[INFO] Generowanie treści przez Claude API…")
    try:
        data = generate_post_via_claude(topic, rag_context)
    except Exception as e:
        print(f"[ERROR] Generacja treści nieudana: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Wyrenderuj HTML i zapisz
    target_dir.mkdir(parents=True, exist_ok=True)
    html = render_post_html(data, slug)
    (target_dir / "index.html").write_text(html, "utf-8")
    print(f"[OK] Zapisano: blog/{slug}/index.html")

    # 5. Zaktualizuj listę, sitemap, RSS
    posts = collect_all_posts()
    update_blog_index(posts)
    generate_sitemap(posts)
    generate_rss(posts)

    print("=" * 60)
    print(f"[DONE] Opublikowano: {data['title']}")
    print(f"[URL]  {DOMAIN}/blog/{slug}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
