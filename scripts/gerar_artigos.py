#!/usr/bin/env python3
"""Gera artigos.html e artigos/<slug>.html a partir de artigos/artigos.json.

Para publicar um artigo novo: acrescente um item no começo de artigos/artigos.json
(slug, titulo, subtitulo, data AAAA-MM-DD, imagem, og, resumo, tag, cor, corpo[])
e rode:  python scripts/gerar_artigos.py

No corpo: "## Título" vira intertítulo; linhas "1. ..." viram lista numerada;
[texto](link) vira link. Nunca editar as páginas geradas à mão: o gerador reescreve.
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://www.alegre-ser.com.br"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
COR = {"magenta": "--magenta", "teal": "--blue", "mostarda": "--mustard", "terracota": "--terracotta"}

# CSS-base e rodapé: copiados da página do PodSer para manter a identidade do site
base = (ROOT / "podser.html").read_text(encoding="utf-8")
css = base[base.find("<style") + 7: base.find("</style>")]
CSS_BASE = css[css.find(":root"): css.find("section{position:relative")]
_f = css.find("footer{background")
CSS_FOOT = css[_f: css.find("@media(max-width:900px)", _f)]
HEAD_FONTS = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;0,700;1,500;1,600&family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">'''
HEADER = base[base.find("<header>"): base.find("</header>") + 9]
FOOTER = base[base.find("<footer>"): base.find("</footer>") + 9]
if 'href="/artigos.html"' not in HEADER:
    HEADER = HEADER.replace('<a href="/podser.html">PodSer</a>',
                            '<a href="/podser.html">PodSer</a>\n      <a href="/artigos.html">Artigos</a>', 1)
if 'href="/artigos.html"' not in FOOTER:
    FOOTER = FOOTER.replace('<li><a href="/podser.html">PodSer</a></li>',
                            '<li><a href="/podser.html">PodSer</a></li>\n          <li><a href="/artigos.html">Artigos</a></li>', 1)

CSS_EXTRA = """
  .kicker{font-family:var(--font-heading); font-size:12px; letter-spacing:.12em; text-transform:uppercase; color:var(--magenta); margin-bottom:16px;}
  h2.section-title{font-family:var(--font-display); font-size:40px; font-weight:600; margin-bottom:16px; line-height:1.15;}
  p.section-lead{color:var(--muted); font-size:17px; max-width:600px; margin:0 auto 20px;}
  .intro-block{max-width:680px; margin:0 auto 30px; text-align:center;}
  .art-hero{padding:90px 0 30px;}
  .art-head{max-width:760px; margin:0 auto; text-align:center;}
  .art-kicker{font-family:var(--font-heading); font-size:12px; letter-spacing:.12em; text-transform:uppercase; margin-bottom:18px;}
  h1.art-title{font-family:var(--font-display); font-weight:600; font-size:44px; line-height:1.15; margin-bottom:18px;}
  .art-sub{color:var(--muted); font-size:18px; max-width:620px; margin:0 auto 18px;}
  .art-meta{font-family:var(--font-heading); font-size:13px; color:var(--muted);}
  .prose{max-width:720px; margin:0 auto; padding:30px 24px 20px; font-size:18px; line-height:1.78;}
  .prose p{margin-bottom:22px;}
  .prose h2{font-family:var(--font-display); font-size:28px; line-height:1.25; margin:44px 0 16px;}
  .prose ol{margin:0 0 24px 22px;}
  .prose li{margin-bottom:12px;}
  .prose a{color:var(--terracotta); font-weight:600; border-bottom:1.5px solid var(--terracotta-soft);}
  .art-cta{max-width:720px; margin:20px auto 80px; padding:0 24px; display:flex; gap:14px; flex-wrap:wrap;}
  .list-hero{padding:100px 0 20px;}
  .art-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:28px; padding:20px 0 90px;}
  .art-card{background:#fff; border:1px solid var(--cream-border); border-radius:22px; overflow:hidden; display:flex; flex-direction:column; transition:transform .2s, box-shadow .2s;}
  .art-card:hover{transform:translateY(-3px); box-shadow:0 18px 36px rgba(20,14,10,.10);}
  .art-card img{width:100%; aspect-ratio:16/9; object-fit:cover; display:block;}
  .art-card .body{padding:22px 24px 26px;}
  .art-card .tag{display:inline-block; font-family:var(--font-heading); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#fff; padding:4px 12px; border-radius:100px; margin-bottom:12px;}
  .art-card h3{font-family:var(--font-display); font-size:22px; line-height:1.25; margin-bottom:10px;}
  .art-card p{color:var(--muted); font-size:15px; margin-bottom:12px;}
  .art-card .more{font-family:var(--font-heading); font-weight:600; font-size:13px; color:var(--terracotta);}
  @media(max-width:900px){
    .foot-grid{grid-template-columns:1fr;}
    h1.art-title{font-size:32px;}
    .nav{flex-wrap:wrap; row-gap:12px; padding:14px 20px;}
    .nav > .btn-primary{margin-left:auto;}
    .navlinks{order:3; flex-basis:100%; justify-content:center; flex-wrap:wrap; gap:7px 12px; font-size:11.5px;}
    .navlinks a{white-space:nowrap;}
    .wrap{padding:0 20px;}
    .prose{font-size:17px;}
  }
"""


def esc(t): return html.escape(t, quote=True)


def inline(t):
    t = esc(t)
    return re.sub(r"\[([^\]]+)\]\(((?:https?://|/)[^)\s]+)\)",
                  lambda m: f'<a href="{m.group(2)}"' + (' target="_blank" rel="noopener"' if m.group(2).startswith("http") else "") + f'>{m.group(1)}</a>', t)


def corpo_html(blocos):
    out = []
    exp = []
    for b in blocos:  # "## Título\ntexto" => intertítulo + bloco seguinte
        if b.startswith("## ") and "\n" in b:
            h, resto = b.split("\n", 1)
            exp += [h, resto.strip()]
        else:
            exp.append(b)
    for b in exp:
        if b.startswith("## "):
            out.append(f"<h2>{inline(b[3:].strip())}</h2>")
        elif re.match(r"^\d+\. ", b.split("\n")[0]) :
            itens = [re.sub(r"^\d+\.\s*", "", l) for l in b.split("\n") if l.strip()]
            out.append("<ol>" + "".join(f"<li>{inline(i)}</li>" for i in itens) + "</ol>")
        else:
            out.append(f"<p>{inline(b)}</p>")
    return "\n".join(out)


def data_pt(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def pagina(titulo, desc, canon, og, corpo_pag, extra_head=""):
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(titulo)} — Alegre-Ser</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Alegre-Ser">
<meta property="og:locale" content="pt_BR">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(titulo)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}{og}">
{HEAD_FONTS}
{extra_head}
<style>
  {CSS_BASE}
  {CSS_FOOT}
  {CSS_EXTRA}
</style>
</head>
<body>
{HEADER}
{corpo_pag}
{FOOTER}
</body>
</html>
'''


def main():
    arts = json.loads((ROOT / "artigos" / "artigos.json").read_text(encoding="utf-8"))
    arts.sort(key=lambda a: a["data"], reverse=True)
    for a in arts:
        cor = COR.get(a.get("cor", "magenta"), "--magenta")
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["titulo"],
              "description": a["resumo"], "datePublished": a["data"], "inLanguage": "pt-BR",
              "image": SITE + a["og"], "mainEntityOfPage": f"{SITE}/artigos/{a['slug']}.html",
              "author": {"@type": "Organization", "name": "Alegre-Ser"},
              "publisher": {"@type": "Organization", "name": "Alegre-Ser"}}
        botoes = ""
        if a.get("youtube"):
            botoes += f'<a class="btn btn-primary" href="{a["youtube"]}" target="_blank" rel="noopener">Assistir no YouTube</a>'
        if a.get("spotify"):
            botoes += f'<a class="btn btn-outline" href="{a["spotify"]}" target="_blank" rel="noopener">Ouvir no Spotify</a>'
        corpo = f'''<section class="art-hero"><div class="wrap"><div class="art-head">
  <div class="art-kicker" style="color:var({cor});">{esc(a["tag"])} · Artigo</div>
  <h1 class="art-title">{esc(a["titulo"])}</h1>
  <p class="art-sub">{esc(a["subtitulo"])}</p>
  <div class="art-meta">Alegre-Ser · {data_pt(a["data"])}</div>
</div></div></section>
<article class="prose">
{corpo_html(a["corpo"])}
</article>
<div class="art-cta">{botoes}<a class="btn btn-outline" href="/artigos.html">Ver todos os artigos</a></div>'''
        (ROOT / "artigos" / f"{a['slug']}.html").write_text(
            pagina(a["titulo"], a["resumo"], f"{SITE}/artigos/{a['slug']}.html", a["og"], corpo,
                   f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'),
            encoding="utf-8")
    cards = "\n".join(f'''<a class="art-card" href="/artigos/{a["slug"]}.html">
  <img loading="lazy" src="{a["imagem"]}" alt="">
  <div class="body"><span class="tag" style="background:var({COR.get(a.get("cor","magenta"),"--magenta")});">{esc(a["tag"])}</span>
  <h3>{esc(a["titulo"])}</h3><p>{esc(a["resumo"])}</p><span class="more">Ler artigo →</span></div></a>''' for a in arts)
    lista = f'''<section class="list-hero"><div class="wrap"><div class="intro-block">
  <div class="kicker">Artigos · Alegre-Ser</div>
  <h2 class="section-title" style="margin-left:auto;margin-right:auto;">Consciência no trabalho e na vida</h2>
  <p class="section-lead">Textos que nascem das conversas do PodSer e do Método JDL, para quem lidera pessoas e para quem quer entender o que acontece entre o que a gente sabe e o que a gente faz.</p>
</div></div></section>
<section><div class="wrap"><div class="art-grid">
{cards}
</div></div></section>'''
    (ROOT / "artigos.html").write_text(
        pagina("Artigos", "Artigos do Alegre-Ser sobre consciência, liderança e energia no trabalho e na vida, a partir do Método JDL.",
               f"{SITE}/artigos.html", arts[0]["og"], lista), encoding="utf-8")
    print(f"{len(arts)} artigo(s) gerado(s).")


if __name__ == "__main__":
    sys.exit(main())
