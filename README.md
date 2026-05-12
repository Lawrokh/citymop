# CityMop — strona z modułem bloga AI

Profesjonalna, statyczna strona firmy sprzątającej **CityMop** z Buska-Zdroju.
Zbudowana z myślą o maksymalnej widoczności w **Google** i **AI Search**
(ChatGPT, Perplexity, Google AI Mode, Claude, Gemini).

---

## 📐 Stack technologiczny

| Warstwa | Technologia | Powód wyboru |
|---|---|---|
| **Strona główna** | Czysty HTML + CSS + Vanilla JS | Pełny HTML w pierwszym requestcie → idealny pod GPTBot/ClaudeBot/PerplexityBot (nie wykonują JS). Maksymalne Core Web Vitals. |
| **Blog** | Statyczne strony HTML generowane przez skrypt Python | Każdy post = osobny plik HTML z pełnym Schema.org. AI crawlery widzą natychmiast cały kontent. |
| **Generacja postów** | Claude API (`claude-opus-4-7`) + RAG z encyklopedią SEO | Wysokiej jakości, semantycznie poprawne treści (BLUF, Atomic Claims, autonomiczność chunków). |
| **Automatyzacja** | GitHub Actions cron (1× dziennie) | Zero kosztów hostingu, pełna kontrola wersji, commit per post. |
| **Hosting** | GitHub Pages / Vercel / Netlify | Wszystkie obsługują statyczne pliki za darmo. CDN globalne. |

---

## 🗂 Struktura katalogów

```
citymop/
├── index.html                       # Strona główna
├── robots.txt                       # Zezwolenia dla Google + AI crawlerów
├── sitemap.xml                      # Mapa strony (auto-aktualizowana)
├── README.md                        # Ten plik
│
├── css/
│   └── style.css                    # Cała estetyka (~900 linii)
│
├── js/
│   └── main.js                      # Interakcje (nav, FAQ, smooth scroll)
│
├── blog/
│   ├── index.html                   # Lista wpisów (auto-aktualizowana)
│   ├── feed.xml                     # RSS feed
│   ├── jak-prac-kanape-w-domu/
│   │   └── index.html
│   ├── sprzatanie-po-remoncie-od-czego-zaczac/
│   │   └── index.html
│   └── ile-kosztuje-sprzatanie-mieszkania-busko/
│       └── index.html
│
├── scripts/
│   ├── build_blog.py                # Generator postów
│   ├── topics_pool.json             # Pula tematów do rozszerzania
│   └── seo_encyklopedia_rag.jsonl   # Baza wiedzy SEO (265 wpisów)
│
├── assets/
│   ├── favicon.svg
│   └── logo.svg
│
└── .github/workflows/
    └── daily-blog.yml               # Cron GitHub Actions
```

---

## 🚀 Wdrożenie — krok po kroku

### Wariant A: GitHub Pages (najprostsze, darmowe)

1. Załóż konto na **github.com** (jeśli nie masz).
2. Stwórz nowe repozytorium publiczne, np. `citymop-pl`.
3. Wgraj wszystkie pliki z tego folderu do repozytorium:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TWOJ-LOGIN/citymop-pl.git
   git push -u origin main
   ```
4. W ustawieniach repo: **Settings → Pages → Source: deploy from branch `main` / root**.
5. Strona dostępna pod `https://TWOJ-LOGIN.github.io/citymop-pl/`.
6. Aby podpiąć własną domenę **citymop.pl**:
   - W ustawieniach Pages dodaj custom domain.
   - U dostawcy domeny ustaw rekord **CNAME**: `@ → TWOJ-LOGIN.github.io`.

### Wariant B: Vercel (szybsze, lepsze CDN)

1. Konto na **vercel.com**, połącz z GitHub.
2. Import repozytorium → automatyczny deploy.
3. Custom domain w Dashboardzie → wpisz `citymop.pl`.

### Wariant C: Netlify

1. Konto na **netlify.com**.
2. Drag & drop folderu lub połącz z GitHub.

---

## 🤖 Uruchomienie automatycznego bloga AI

### 1. Wygeneruj klucz API Claude

- Zaloguj się na **console.anthropic.com**.
- Sekcja **API Keys** → **Create Key**.
- Skopiuj klucz (zaczyna się od `sk-ant-...`).

### 2. Dodaj klucz do GitHub Secrets

- W repo: **Settings → Secrets and variables → Actions → New repository secret**.
- Nazwa: `ANTHROPIC_API_KEY`
- Wartość: wklej swój klucz.

### 3. Sprawdź, że plik RAG jest w repo

Plik `scripts/seo_encyklopedia_rag.jsonl` (265 wpisów wiedzy o SEO/GEO)
musi być w repozytorium — jest sercem jakości treści.

### 4. Uruchom workflow ręcznie (test)

- **Actions → Daily Blog Post Generation → Run workflow**.
- Po 1–2 minutach w repo pojawi się nowy commit z postem.
- Workflow działa też automatycznie codziennie o **9:00 czasu polskiego**.

### Koszt operacyjny

| Element | Koszt |
|---|---|
| Hosting (Pages/Vercel/Netlify) | 0 zł / mies. |
| GitHub Actions (2000 min/mies. darmowe) | 0 zł / mies. (post ~30 sek) |
| Claude API | ~0,15–0,30 zł za post (claude-opus-4-7, ~8k tokenów) |
| **Razem (30 postów/mies.)** | **~6–10 zł / mies.** |

---

## ✏️ Personalizacja

### Dodaj własne tematy

Edytuj `scripts/topics_pool.json`:
```json
[
  "Twój nowy temat 1",
  "Twój nowy temat 2"
]
```

### Zmień nazwę firmy / dane kontaktowe

Wszystkie informacje o firmie są w `index.html` (sekcje `<script type="application/ld+json">`)
oraz w stałej `SYSTEM_PROMPT_TEMPLATE` w `scripts/build_blog.py`.

### Zmień stylistykę

Zmienne CSS na początku `css/style.css` (sekcja `:root`):
```css
--c-zdroj: #14498f;     /* kolor główny (deep brand blue z loga) */
--c-zest:  #117cc4;     /* akcent (sky blue z fali w logo) */
--c-paper: #f5f8fc;     /* tło (cool paper) */
```

### Wyłącz codzienną generację

W `.github/workflows/daily-blog.yml` zakomentuj sekcję `schedule:` —
zostanie tylko ręczne uruchamianie (`workflow_dispatch`).

---

## 🧪 Lokalne uruchomienie

```bash
# Serwer HTTP do podglądu w przeglądarce
python -m http.server 8000

# Generacja nowego postu lokalnie (wymaga ANTHROPIC_API_KEY w env)
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/build_blog.py
```

---

## 🎯 Co już jest zoptymalizowane

### SEO (Google)
- ✅ Wszystkie meta-tagi (title, description, keywords, canonical)
- ✅ Geo meta tagi + ICBM coordinates (Busko-Zdrój)
- ✅ Open Graph + Twitter Cards
- ✅ Sitemap.xml + RSS
- ✅ Schema.org JSON-LD: LocalBusiness, CleaningService, FAQPage, Article, HowTo, BreadcrumbList
- ✅ Semantyczny HTML (article, header, nav, section)
- ✅ Pełne wsparcie urządzeń mobilnych
- ✅ Core Web Vitals — czysty statyczny HTML

### GEO / AI Search (ChatGPT, Perplexity, Claude, Gemini, AI Mode)
- ✅ **BLUF** — bezpośrednia odpowiedź w pierwszych 50 słowach na każdej stronie
- ✅ **Atomic Claims** — twierdzenia weryfikowalne z liczbami (150 zł, 60-90 min, 14 dni)
- ✅ **Central Entity** — CityMop jako Agent w stronie czynnej
- ✅ **Autonomiczność chunków** — każda sekcja H2 zrozumiała samodzielnie
- ✅ **E-E-A-T** — autor (Zespół CityMop), doświadczenie (8 lat), liczby
- ✅ **robots.txt** — jawnie zezwala wszystkim AI crawlerom
- ✅ FAQ z dokładną odpowiednością HTML ↔ JSON-LD (anti-divergence)

### Lokalne SEO (Busko-Zdrój)
- ✅ NAP (Name-Address-Phone) konsekwentne wszędzie
- ✅ Google Maps embed z dokładną lokalizacją
- ✅ Lista 12 miejscowości obsługiwanych
- ✅ areaServed w Schema.org
- ✅ Linki do Facebooka i Google Maps Place

---

## 📝 Zasady pisania w blogu (egzekwowane przez prompt)

Wszystkie generowane przez AI posty:
1. Zaczynają od BLUF (40–55 słów z liczbami)
2. Mają H1, lead, 2 paragrafy intro, 4–7 sekcji H2
3. Każda sekcja H2 jest autonomiczna (żadnych „jak wspomniano powyżej")
4. CityMop występuje w stronie czynnej jako podmiot zdań
5. 3–5 FAQ z odpowiedziami 40–70 słów
6. HowTo steps (jeśli temat instruktażowy)
7. Pełne Schema.org: Article + HowTo + FAQPage
8. CTA w stopce artykułu kierujące do `/#kontakt`

---

## 📞 Kontakt CityMop

- **Telefon:** +48 530 610 336
- **E-mail:** info@citymop.pl
- **Facebook:** [@sprzataniebusko](https://www.facebook.com/sprzataniebusko/)
- **Adres:** Busko-Zdrój 28-100, woj. świętokrzyskie

---

## 📄 Licencja

Kod i treść należą do CityMop. Encyklopedia SEO (`seo_encyklopedia_rag.jsonl`) —
zgodnie z licencją autora.
