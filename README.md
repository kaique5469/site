# Capital Inteligente — Blog de Finanças

Blog de finanças com publicação automática via GitHub Actions + Claude API.

---

## ⚡ Setup em 5 passos

### 1. Crie o repositório no GitHub

1. Acesse [github.com](https://github.com) → **New repository**
2. Nome: `capital-inteligente` (ou qualquer outro)
3. Visibilidade: **Public** (necessário para GitHub Pages gratuito)
4. **Não** inicialize com README (você já tem os arquivos)
5. Clique em **Create repository**

### 2. Suba os arquivos

No terminal, dentro da pasta `capital-inteligente-site`:

```bash
git init
git add .
git commit -m "🚀 Primeiro deploy — Capital Inteligente"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/capital-inteligente.git
git push -u origin main
```

### 3. Ative o GitHub Pages

1. No repositório → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / pasta: `/ (root)`
4. Salve — o site fica disponível em `SEU_USUARIO.github.io/capital-inteligente`

### 4. Adicione a chave da API

1. No repositório → **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret**
3. Nome: `ANTHROPIC_API_KEY`
4. Valor: sua chave da API Anthropic (obtenha em [console.anthropic.com](https://console.anthropic.com))

> Não tem chave? Crie em **console.anthropic.com** → API Keys → Create Key. Há crédito gratuito para começar.

### 5. Configure o domínio (opcional mas recomendado)

**Compre um domínio** (sugestões):
- `capitalinteligente.com.br` — R$ ~40/ano no Registro.br
- `capitalinteligente.com` — ~USD 12/ano no Namecheap/GoDaddy

**Configure o DNS** (no painel do seu registrador):
```
Tipo    Nome    Valor
A       @       185.199.108.153
A       @       185.199.109.153
A       @       185.199.110.153
A       @       185.199.111.153
CNAME   www     SEU_USUARIO.github.io
```

**No GitHub:** Settings → Pages → Custom domain → insira seu domínio

O arquivo `CNAME` já está configurado. Só troque o domínio dentro dele se for diferente.

---

## 📰 Como funciona a publicação

### Automática (todo dia)
- **08:00 BRT** — Edição da manhã (6 artigos)
- **14:00 BRT** — Edição da tarde, seg–sex (atualização de mercado)

### Breaking news (manual)
1. Vá em **Actions** → **📰 Publicar Artigos** → **Run workflow**
2. Preencha o campo **"⚡ Notícia urgente"** com o tema
3. Clique em **Run workflow**

O script vai gerar artigos com foco nessa notícia e publicar em minutos.

---

## 🔧 Personalização

### Mudar quantidade de artigos
No workflow (`generate-articles.yml`), altere o valor padrão de `num_articles`:
```yaml
default: "8"  # aumenta para 8 artigos por edição
```

### Mudar horários de publicação
Edite as linhas `cron` no workflow. Lembre: GitHub usa UTC (BRT = UTC-3).
```yaml
- cron: "0 11 * * *"   # 08:00 BRT
- cron: "0 17 * * 1-5" # 14:00 BRT (seg-sex)
```

### Atualizar contexto de mercado
No arquivo `scripts/generate_articles.py`, atualize a variável `MARKET_CONTEXT_2026` com os dados mais recentes — Selic, Ibovespa, Dólar, etc.

---

## 📁 Estrutura do projeto

```
capital-inteligente/
├── index.html                    # Homepage do blog (SEO otimizado)
├── articles.json                 # Lista de artigos (atualizado pelo script)
├── sitemap.xml                   # Sitemap para Google (atualizado pelo script)
├── robots.txt                    # Permissões para crawlers
├── CNAME                         # Domínio customizado
├── artigos/                      # Páginas individuais de cada artigo
│   └── 2026-05-26-titulo.html   # Geradas automaticamente
├── scripts/
│   └── generate_articles.py     # Script de geração de artigos
└── .github/
    └── workflows/
        └── generate-articles.yml # Automação GitHub Actions
```

---

## 🔍 SEO — Submeter ao Google

Após o primeiro deploy com artigos:

1. Acesse [search.google.com/search-console](https://search.google.com/search-console)
2. Adicione seu domínio como propriedade
3. Vá em **Sitemaps** → Insira `https://seudominio.com/sitemap.xml`
4. Aguarde a indexação (pode levar alguns dias)

---

Desenvolvido com Claude API (Anthropic) · Hospedado no GitHub Pages
