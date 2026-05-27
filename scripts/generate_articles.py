#!/usr/bin/env python3
"""
Capital Inteligente — Gerador automático de artigos
Roda via GitHub Actions toda manhã e em breaking news.
"""

import os
import json
import re
import sys
import unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path

import anthropic

# ── CONFIGURAÇÃO ────────────────────────────────────────────────────────────
SITE_DIR   = Path(__file__).parent.parent
ARTIGOS_DIR = SITE_DIR / "artigos"
ARTICLES_JSON = SITE_DIR / "articles.json"
SITEMAP_FILE  = SITE_DIR / "sitemap.xml"
DOMAIN = os.getenv("SITE_DOMAIN", "capitalinteligente.com.br")

# Contexto fixo de mercado (atualizado automaticamente por data no prompt)
MARKET_CONTEXT_2026 = """
- Ibovespa em torno de 176.000 pontos, com volatilidade em maio
- Dólar em R$ 4,91 — menor nível em mais de 2 anos, queda de 10,5% no ano
- Selic em 14,25% a.a., com ciclo de corte em andamento (Citi projeta 13,75% até dez/2026)
- IPCA-15 e dados de inflação sendo monitorados de perto
- Ano eleitoral gera cautela na renda variável, mas ciclo de corte de juros favorece bolsa
- Bitcoin e criptomoedas em linha com volatilidade do mercado global
- Governo pressionado pelo fiscal; debate sobre arcabouço fiscal em foco
"""

# Descrições do Cento por categoria (para o bloco de recomendação no final de cada artigo)
CENTO_BY_CATEGORY = {
    "Saúde Financeira": "Veja exatamente para onde vai cada real. O Cento categoriza seus gastos com IA e mostra onde cortar sem achismo.",
    "Investimentos":    "Acompanhe carteira, metas e mercado ao vivo em um único lugar, com projeção personalizada de 12 meses.",
    "Renda Fixa":       "Defina suas metas financeiras e veja mês a mês quando vai atingi-las, com plano adaptado ao seu perfil.",
    "Renda Variável":   "Acompanhe Ibovespa, dólar e ações em tempo real — com alertas contextuais para tomar decisões melhores.",
    "Criptomoedas":     "Bitcoin, Ethereum, dólar e mais em tempo real. O Cento avisa quando algo importante acontece no mercado.",
}


# ── SLUGIFY ─────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:70]


# ── BODY → HTML ──────────────────────────────────────────────────────────────
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


# ── GERAR ARTIGOS VIA API ────────────────────────────────────────────────────
def generate_articles(breaking_topic: str | None = None, num_articles: int = 6) -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today_str = datetime.now().strftime("%d de %B de %Y")

    breaking_instruction = ""
    if breaking_topic:
        breaking_instruction = f"""
⚡ NOTÍCIA URGENTE DO DIA: {breaking_topic}
O PRIMEIRO artigo DEVE abordar essa notícia urgente com análise aprofundada.
Adapte os outros artigos para refletir o impacto dessa notícia no mercado.
"""

    prompt = f"""Você é um jornalista financeiro sênior do blog "Capital Inteligente", especializado em finanças pessoais e mercado de capitais brasileiro.

CONTEXTO DO MERCADO HOJE ({today_str}):
{MARKET_CONTEXT_2026}
{breaking_instruction}

Escreva EXATAMENTE {num_articles} artigos originais, analíticos e baseados no contexto acima.
Tom: colunista experiente — direto, prático, com profundidade. Sem jargão excessivo.
Cada artigo deve trazer valor real ao leitor brasileiro que quer entender e melhorar suas finanças.

Responda SOMENTE com um JSON array válido (sem markdown, sem explicações). Formato:
[
  {{
    "title": "Título impactante e preciso (máx. 80 caracteres)",
    "category": "Investimentos",
    "summary": "Lide em 2-3 frases — o que o leitor aprende ou ganha com a leitura.",
    "readTime": "5",
    "body": "Corpo do artigo em 4-5 parágrafos. Use ## para subtítulos e > para destaques editoriais. Tom analítico e prático. Cada parágrafo separado por linha em branco.",
    "tags": ["palavra-chave-1", "palavra-chave-2", "palavra-chave-3"]
  }}
]

Regras:
- Inclua pelo menos 1 artigo de cada categoria: Investimentos, Renda Fixa, Renda Variável, Saúde Financeira, Criptomoedas
- O primeiro artigo é o destaque do dia — mais urgente e impactante
- Tags devem ser em português, lowercase, com hífen (ex: "renda-fixa", "selic", "tesouro-direto")
- Categorias válidas: Investimentos, Renda Fixa, Renda Variável, Saúde Financeira, Criptomoedas"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=10000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text
    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        return json.loads(match.group(0))
    return json.loads(content)


# ── GERAR PÁGINA HTML DO ARTIGO ──────────────────────────────────────────────
def render_article_page(article: dict, slug: str, date_iso: str) -> str:
    body_html  = body_to_html(article.get("body", ""))
    cento_desc = CENTO_BY_CATEGORY.get(article["category"], "Controle gastos, defina metas e acompanhe investimentos com IA.")
    tags_html  = " ".join(f'<a class="tag" href="/#tag-{t}">{t}</a>' for t in article.get("tags", []))
    date_br    = datetime.fromisoformat(date_iso).strftime("%d de %B de %Y")
    summary_esc = article["summary"].replace('"', "&quot;")
    title_esc   = article["title"].replace('"', "&quot;")

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
<meta property="article:section" content="{article["category"]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://{DOMAIN}/artigos/{slug}.html">
<link rel="icon" href="/favicon.ico">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{title_esc}",
  "description": "{summary_esc[:155]}",
  "datePublished": "{date_iso}",
  "dateModified": "{date_iso}",
  "author": {{"@type": "Organization", "name": "Capital Inteligente", "url": "https://{DOMAIN}"}},
  "publisher": {{"@type": "Organization", "name": "Capital Inteligente", "url": "https://{DOMAIN}"}},
  "url": "https://{DOMAIN}/artigos/{slug}.html",
  "articleSection": "{article["category"]}"
}}
</script>
<style>
:root {{
  --bg: #060d1f; --bg2: #0d1a35; --card: #0f2040;
  --accent: #00d68f; --glow: rgba(0,214,143,.15);
  --text: #e8f0fe; --muted: #8ba4c8; --dim: #4a6080;
  --border: #1a3050; --border-a: #00d68f40;
}}
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; line-height:1.7; }}
a {{ color:var(--accent); }}

/* HEADER */
header {{ background:#070e22; border-bottom:1px solid var(--border); padding:0 24px; position:sticky; top:0; z-index:50; }}
.header-inner {{ max-width:800px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; height:60px; }}
.logo {{ display:flex; align-items:center; gap:10px; text-decoration:none; }}
.logo-icon {{ width:32px; height:32px; background:linear-gradient(135deg,var(--accent),#00a8ff); border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:15px; font-weight:900; color:#060d1f; }}
.logo-text {{ font-size:16px; font-weight:700; color:var(--text); }}
.logo-text span {{ color:var(--accent); }}
.back-link {{ font-size:13px; color:var(--muted); text-decoration:none; }}
.back-link:hover {{ color:var(--accent); }}

/* ARTICLE */
main {{ max-width:800px; margin:0 auto; padding:48px 24px 80px; }}
.article-meta {{ display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:20px; }}
.category-tag {{ font-size:11px; font-weight:700; padding:3px 10px; border-radius:100px; text-transform:uppercase; letter-spacing:.5px; background:#1a3a6a; color:#6ab0ff; }}
.category-tag.rf  {{ background:#1a3a2a; color:#5ddba0; }}
.category-tag.rv  {{ background:#3a1a3a; color:#d47aff; }}
.category-tag.sf  {{ background:#3a2a1a; color:#ffb347; }}
.category-tag.btc {{ background:#1a2a3a; color:#f7931a; }}
.article-date, .read-time {{ font-size:12px; color:var(--dim); }}
h1 {{ font-size:clamp(22px,4vw,34px); font-weight:800; line-height:1.25; letter-spacing:-.5px; margin-bottom:18px; }}
.article-lead {{ font-size:18px; color:var(--muted); line-height:1.7; margin-bottom:32px; padding-bottom:28px; border-bottom:1px solid var(--border); font-style:italic; }}
.article-body h2 {{ font-size:20px; font-weight:700; color:var(--text); margin:28px 0 12px; }}
.article-body p {{ font-size:16px; color:var(--muted); margin-bottom:18px; }}
.article-body strong {{ color:var(--text); }}
.article-body blockquote {{ background:var(--glow); border-left:3px solid var(--accent); border-radius:0 8px 8px 0; padding:12px 18px; margin:20px 0; }}
.article-body blockquote p {{ margin:0; font-style:italic; }}
.tags {{ margin-top:28px; display:flex; flex-wrap:wrap; gap:8px; }}
.tag {{ font-size:12px; background:var(--card); border:1px solid var(--border); border-radius:100px; padding:3px 10px; color:var(--dim); text-decoration:none; }}
.tag:hover {{ border-color:var(--border-a); color:var(--accent); }}

/* CENTO BLOCK */
.cento-block {{ margin-top:40px; padding-top:28px; border-top:1px solid var(--border); }}
.cento-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1.2px; color:var(--dim); margin-bottom:12px; }}
.cento-card {{ display:flex; align-items:center; gap:14px; background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:16px; text-decoration:none; transition:border-color .2s,background .2s; }}
.cento-card:hover {{ border-color:var(--border-a); background:var(--card); }}
.cento-icon {{ width:42px; height:42px; background:linear-gradient(135deg,#1a1a2e,#16213e); border:1px solid var(--border); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; font-weight:900; color:var(--accent); flex-shrink:0; }}
.cento-info {{ flex:1; }}
.cento-info strong {{ display:block; font-size:14px; color:var(--text); margin-bottom:2px; }}
.cento-info span {{ font-size:12px; color:var(--muted); }}
.cento-cta {{ font-size:12px; font-weight:700; color:var(--accent); white-space:nowrap; }}

/* FOOTER */
footer {{ text-align:center; padding:28px 24px; border-top:1px solid var(--border); }}
footer p {{ font-size:12px; color:var(--dim); line-height:1.8; }}
footer a {{ color:var(--accent); text-decoration:none; }}
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <a class="logo" href="/">
      <div class="logo-icon">CI</div>
      <span class="logo-text">Capital <span>Inteligente</span></span>
    </a>
    <a class="back-link" href="/">← Todos os artigos</a>
  </div>
</header>

<main>
  <div class="article-meta">
    <span class="category-tag {{"rf" if article["category"]=="Renda Fixa" else "rv" if article["category"]=="Renda Variável" else "sf" if article["category"]=="Saúde Financeira" else "btc" if article["category"]=="Criptomoedas" else ""}}">{article["category"]}</span>
    <span class="article-date">{date_br}</span>
    <span class="read-time">⏱ {article.get("readTime","5")} min de leitura</span>
  </div>

  <h1>{article["title"]}</h1>
  <p class="article-lead">{article["summary"]}</p>

  <div class="article-body">
    {body_html}
  </div>

  <div class="tags">{tags_html}</div>

  <div class="cento-block">
    <div class="cento-label">Ferramenta recomendada pela redação</div>
    <a class="cento-card" href="https://mycento.finance/finance-app.html" target="_blank" rel="noopener">
      <div class="cento-icon">C</div>
      <div class="cento-info">
        <strong>Cento — Finanças Inteligentes</strong>
        <span>{cento_desc}</span>
      </div>
      <span class="cento-cta">Testar grátis →</span>
    </a>
  </div>
</main>

<footer>
  <p>
    <a href="/">Capital Inteligente</a> — Blog de Finanças &amp; Investimentos<br>
    Conteúdo de caráter informativo e educativo. Não constitui recomendação de investimento.
  </p>
</footer>
</body>
</html>"""


# ── ATUALIZAR INDEX ──────────────────────────────────────────────────────────
def load_existing_articles() -> list[dict]:
    if ARTICLES_JSON.exists():
        with open(ARTICLES_JSON, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_articles(articles: list[dict]):
    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


# ── GERAR SITEMAP ────────────────────────────────────────────────────────────
def update_sitemap(articles: list[dict]):
    today = date.today().isoformat()
    urls = [f"""  <url>
    <loc>https://{DOMAIN}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""]

    for a in articles[:50]:  # máx 50 artigos no sitemap
        urls.append(f"""  <url>
    <loc>https://{DOMAIN}/artigos/{a["slug"]}.html</loc>
    <lastmod>{a["date"]}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap)
    print(f"✅ Sitemap atualizado ({len(urls)} URLs)")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    breaking_topic = os.getenv("BREAKING_TOPIC") or (sys.argv[1] if len(sys.argv) > 1 else None)
    num_articles   = int(os.getenv("NUM_ARTICLES", "6"))

    if breaking_topic:
        print(f"⚡ Modo breaking news: {breaking_topic}")
        num_articles = max(num_articles, 6)
    else:
        print(f"📰 Gerando {num_articles} artigos para {date.today().isoformat()}...")

    # Gera artigos
    articles_raw = generate_articles(breaking_topic, num_articles)
    print(f"✅ {len(articles_raw)} artigos gerados pela API")

    # Garante que o diretório existe
    ARTIGOS_DIR.mkdir(exist_ok=True)

    today_iso = date.today().isoformat()
    new_entries = []

    for art in articles_raw:
        slug = f"{today_iso}-{slugify(art['title'])}"
        html = render_article_page(art, slug, today_iso)

        # Salva página do artigo
        page_path = ARTIGOS_DIR / f"{slug}.html"
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)

        new_entries.append({
            "id":       slug,
            "slug":     slug,
            "title":    art["title"],
            "category": art["category"],
            "summary":  art["summary"],
            "readTime": art.get("readTime", "5"),
            "tags":     art.get("tags", []),
            "date":     today_iso,
            "breaking": bool(breaking_topic),
        })
        print(f"  📄 /artigos/{slug}.html")

    # Carrega histórico e adiciona novos no topo
    existing = load_existing_articles()
    all_articles = new_entries + existing

    # Mantém somente os últimos 60 artigos no JSON
    all_articles = all_articles[:60]
    save_articles(all_articles)

    # Atualiza sitemap
    update_sitemap(all_articles)

    print(f"\n🎉 Publicação concluída! {len(new_entries)} novos artigos adicionados.")
    if breaking_topic:
        print(f"⚡ Breaking news cobrindo: {breaking_topic}")


if __name__ == "__main__":
    main()
