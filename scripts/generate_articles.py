#!/usr/bin/env python3
"""
Capital Inteligente — Gerador automático de artigos
Usa OpenRouter API (gratuita) via GitHub Actions.
"""

import os
import json
import re
import sys
import time
import urllib.request
import urllib.error
import unicodedata
from datetime import datetime, date
from pathlib import Path

# ── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
SITE_DIR    = Path(__file__).parent.parent
ARTIGOS_DIR = SITE_DIR / "artigos"
ARTICLES_JSON = SITE_DIR / "articles.json"
SITEMAP_FILE  = SITE_DIR / "sitemap.xml"
DOMAIN = os.getenv("SITE_DOMAIN", "capitalinteligente.com.br")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

MARKET_CONTEXT = """
- Ibovespa em torno de 176.000 pontos, com volatilidade em maio
- Dólar em R$ 4,91 — menor nível em mais de 2 anos, queda de 10,5% no ano
- Selic em 14,25% a.a., com ciclo de corte em andamento
- IPCA-15 e dados de inflação sendo monitorados de perto
- Ano eleitoral gera cautela na renda variável
- Bitcoin e criptomoedas em linha com volatilidade do mercado global
"""

CENTO_BY_CATEGORY = {
    "Saúde Financeira": "Veja exatamente para onde vai cada real. O Cento categoriza seus gastos com IA e mostra onde cortar sem achismo.",
    "Investimentos":    "Acompanhe carteira, metas e mercado ao vivo em um único lugar, com projeção personalizada de 12 meses.",
    "Renda Fixa":       "Defina suas metas financeiras e veja mês a mês quando vai atingi-las, com plano adaptado ao seu perfil.",
    "Renda Variável":   "Acompanhe Ibovespa, dólar e ações em tempo real — com alertas contextuais para tomar decisões melhores.",
    "Criptomoedas":     "Bitcoin, Ethereum, dólar e mais em tempo real. O Cento avisa quando algo importante acontece no mercado.",
}


# ── OPENROUTER API ───────────────────────────────────────────────────────────
def call_groq(prompt: str) -> str:
    """Chama OpenRouter (compatível com OpenAI). Nome mantido por compatibilidade."""
    payload = json.dumps({
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 8192,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": f"https://{DOMAIN}",
            "X-Title": "Capital Inteligente",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[erro OpenRouter] HTTP {e.code}: {body}")
        raise


# ── GERAR ARTIGOS ─────────────────────────────────────────────────────────────
def generate_articles(breaking_topic: str | None = None, num_articles: int = 6) -> list[dict]:
    today_str = datetime.now().strftime("%d de %B de %Y")

    breaking_instruction = ""
    if breaking_topic:
        breaking_instruction = f"""
⚡ NOTÍCIA URGENTE DO DIA: {breaking_topic}
O PRIMEIRO artigo DEVE abordar essa notícia com análise aprofundada.
"""

    prompt = f"""Você é um jornalista financeiro sênior do blog "Capital Inteligente".

CONTEXTO DO MERCADO HOJE ({today_str}):
{MARKET_CONTEXT}
{breaking_instruction}

Escreva EXATAMENTE {num_articles} artigos originais e analíticos.
Tom: colunista experiente — direto, prático, sem jargão excessivo.

Responda SOMENTE com um JSON array válido (sem markdown, sem texto fora do JSON):
[
  {{
    "title": "Título impactante (máx 80 caracteres)",
    "category": "Investimentos",
    "summary": "Lide em 2-3 frases — o que o leitor aprende.",
    "readTime": "5",
    "body": "Corpo em 4 parágrafos. Use ## para subtítulos e > para destaques. Cada parágrafo separado por linha em branco.",
    "tags": ["palavra-chave-1", "palavra-chave-2"]
  }}
]

Categorias obrigatórias (1 de cada): Investimentos, Renda Fixa, Renda Variável, Saúde Financeira, Criptomoedas.
O primeiro artigo é o destaque do dia — mais urgente e impactante.
IMPORTANTE: responda APENAS o JSON, sem nenhum texto antes ou depois."""

    raw = call_groq(prompt)
    match = re.search(r"\[[\s\S]*\]", raw)
    if match:
        return json.loads(match.group(0))
    return json.loads(raw)


# ── UTILITÁRIOS ───────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:70]

def body_to_html(body: str) -> str:
    parts = []
    for para in body.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("## "):
            parts.append(f"<h2>{para[3:]}</h2>")
        elif para.startswith("> "):
            parts.append(f"<blockquote><p>{para[2:]}</p></blockquote>")
        else:
            para = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", para)
            parts.append(f"<p>{para}</p>")
    return "\n".join(parts)


# ── GERAR PÁGINA HTML DO ARTIGO ───────────────────────────────────────────────
def render_article_page(article: dict, slug: str, date_iso: str) -> str:
    body_html  = body_to_html(article.get("body", ""))
    cento_desc = CENTO_BY_CATEGORY.get(article["category"], "Controle gastos, defina metas e acompanhe investimentos com IA.")
    tags_html  = " ".join(f'<a class="tag" href="/#tag-{t}">{t}</a>' for t in article.get("tags", []))
    date_br    = datetime.fromisoformat(date_iso).strftime("%d de %B de %Y")
    summary_esc = article["summary"].replace('"', "&quot;")
    title_esc   = article["title"].replace('"', "&quot;")

    cat = article["category"]
    cat_cls = {"Renda Fixa":"rf","Renda Variável":"rv","Saúde Financeira":"sf","Criptomoedas":"btc"}.get(cat,"")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{article["title"]} | Capital Inteligente</title>
<meta name="description" content="{summary_esc[:155]}">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{summary_esc[:155]}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://{DOMAIN}/artigos/{slug}.html">
<meta property="og:site_name" content="Capital Inteligente">
<meta property="article:published_time" content="{date_iso}">
<meta property="article:section" content="{cat}">
<link rel="canonical" href="https://{DOMAIN}/artigos/{slug}.html">
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{title_esc}","description":"{summary_esc[:155]}","datePublished":"{date_iso}","dateModified":"{date_iso}","author":{{"@type":"Organization","name":"Capital Inteligente"}},"publisher":{{"@type":"Organization","name":"Capital Inteligente","url":"https://{DOMAIN}"}},"url":"https://{DOMAIN}/artigos/{slug}.html","articleSection":"{cat}"}}
</script>
<style>
:root{{--bg:#060d1f;--bg2:#0d1a35;--card:#0f2040;--card-h:#152850;--accent:#00d68f;--glow:rgba(0,214,143,.15);--text:#e8f0fe;--muted:#8ba4c8;--dim:#4a6080;--border:#1a3050;--border-a:#00d68f40}}
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.7}}
a{{color:var(--accent)}}
header{{background:#070e22;border-bottom:1px solid var(--border);padding:0 24px;position:sticky;top:0;z-index:50}}
.hi{{max-width:800px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:60px}}
.logo{{display:flex;align-items:center;gap:10px;text-decoration:none}}
.li{{width:32px;height:32px;background:linear-gradient(135deg,var(--accent),#00a8ff);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;color:#060d1f}}
.lt{{font-size:16px;font-weight:700;color:var(--text)}}.lt span{{color:var(--accent)}}
.bl{{font-size:13px;color:var(--muted);text-decoration:none}}.bl:hover{{color:var(--accent)}}
main{{max-width:800px;margin:0 auto;padding:48px 24px 80px}}
.am{{display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:20px}}
.ct{{font-size:11px;font-weight:700;padding:3px 10px;border-radius:100px;text-transform:uppercase;letter-spacing:.5px;background:#1a3a6a;color:#6ab0ff}}
.ct.rf{{background:#1a3a2a;color:#5ddba0}}.ct.rv{{background:#3a1a3a;color:#d47aff}}.ct.sf{{background:#3a2a1a;color:#ffb347}}.ct.btc{{background:#1a2a3a;color:#f7931a}}
.ad,.rt{{font-size:12px;color:var(--dim)}}
h1{{font-size:clamp(22px,4vw,34px);font-weight:800;line-height:1.25;letter-spacing:-.5px;margin-bottom:18px}}
.al{{font-size:18px;color:var(--muted);line-height:1.7;margin-bottom:32px;padding-bottom:28px;border-bottom:1px solid var(--border);font-style:italic}}
.ab h2{{font-size:20px;font-weight:700;color:var(--text);margin:28px 0 12px}}
.ab p{{font-size:16px;color:var(--muted);margin-bottom:18px}}
.ab strong{{color:var(--text)}}
.ab blockquote{{background:var(--glow);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;padding:12px 18px;margin:20px 0}}
.ab blockquote p{{margin:0;font-style:italic}}
.tags{{margin-top:28px;display:flex;flex-wrap:wrap;gap:8px}}
.tag{{font-size:12px;background:var(--card);border:1px solid var(--border);border-radius:100px;padding:3px 10px;color:var(--dim);text-decoration:none}}
.tag:hover{{border-color:var(--border-a);color:var(--accent)}}
.cb{{margin-top:40px;padding-top:28px;border-top:1px solid var(--border)}}
.cl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;color:var(--dim);margin-bottom:12px}}
.cc{{display:flex;align-items:center;gap:14px;background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px;text-decoration:none;transition:border-color .2s,background .2s}}
.cc:hover{{border-color:var(--border-a);background:var(--card-h)}}
.ci{{width:42px;height:42px;background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid var(--border);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;color:var(--accent);flex-shrink:0}}
.cn{{flex:1}}.cn strong{{display:block;font-size:14px;color:var(--text);margin-bottom:2px}}.cn span{{font-size:12px;color:var(--muted)}}
.cta{{font-size:12px;font-weight:700;color:var(--accent);white-space:nowrap}}
footer{{text-align:center;padding:28px 24px;border-top:1px solid var(--border)}}
footer p{{font-size:12px;color:var(--dim);line-height:1.8}}
</style>
</head>
<body>
<header>
  <div class="hi">
    <a class="logo" href="/"><div class="li">CI</div><span class="lt">Capital <span>Inteligente</span></span></a>
    <a class="bl" href="/">← Todos os artigos</a>
  </div>
</header>
<main>
  <div class="am">
    <span class="ct {cat_cls}">{cat}</span>
    <span class="ad">{date_br}</span>
    <span class="rt">⏱ {article.get("readTime","5")} min de leitura</span>
  </div>
  <h1>{article["title"]}</h1>
  <p class="al">{article["summary"]}</p>
  <div class="ab">{body_html}</div>
  <div class="tags">{tags_html}</div>
  <div class="cb">
    <div class="cl">Ferramenta recomendada pela redação</div>
    <a class="cc" href="https://mycento.finance/finance-app.html" target="_blank" rel="noopener">
      <div class="ci">C</div>
      <div class="cn"><strong>Cento — Finanças Inteligentes</strong><span>{cento_desc}</span></div>
      <span class="cta">Testar grátis →</span>
    </a>
  </div>
</main>
<footer><p><a href="/">Capital Inteligente</a> — Blog de Finanças &amp; Investimentos<br>Conteúdo informativo e educativo. Não constitui recomendação de investimento.</p></footer>
</body>
</html>"""


# ── SITEMAP ───────────────────────────────────────────────────────────────────
def update_sitemap(articles: list[dict]):
    today = date.today().isoformat()
    urls = [f"  <url><loc>https://{DOMAIN}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    for a in articles[:50]:
        urls.append(f"  <url><loc>https://{DOMAIN}/artigos/{a['slug']}.html</loc><lastmod>{a['date']}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{chr(10).join(urls)}\n</urlset>"""
    SITEMAP_FILE.write_text(sitemap, encoding="utf-8")
    print(f"✅ Sitemap: {len(urls)} URLs")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    breaking_topic = os.getenv("BREAKING_TOPIC") or (sys.argv[1] if len(sys.argv) > 1 else None)
    num_articles   = int(os.getenv("NUM_ARTICLES", "6"))

    print(f"📰 Gerando {num_articles} artigos para {date.today().isoformat()}...")
    if breaking_topic:
        print(f"⚡ Breaking news: {breaking_topic}")

    articles_raw = generate_articles(breaking_topic, num_articles)
    print(f"✅ {len(articles_raw)} artigos gerados")

    ARTIGOS_DIR.mkdir(exist_ok=True)
    today_iso  = date.today().isoformat()
    new_entries = []

    for art in articles_raw:
        slug = f"{today_iso}-{slugify(art['title'])}"
        html = render_article_page(art, slug, today_iso)
        (ARTIGOS_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
        new_entries.append({
            "id": slug, "slug": slug,
            "title": art["title"], "category": art["category"],
            "summary": art["summary"], "readTime": art.get("readTime","5"),
            "tags": art.get("tags",[]), "date": today_iso,
            "breaking": bool(breaking_topic),
        })
        print(f"  📄 /artigos/{slug}.html")

    existing = json.loads(ARTICLES_JSON.read_text(encoding="utf-8")) if ARTICLES_JSON.exists() else []
    all_articles = (new_entries + existing)[:60]
    ARTICLES_JSON.write_text(json.dumps(all_articles, ensure_ascii=False, indent=2), encoding="utf-8")

    update_sitemap(all_articles)
    print(f"\n🎉 {len(new_entries)} artigos publicados!")

if __name__ == "__main__":
    main()
