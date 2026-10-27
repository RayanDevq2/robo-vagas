#!/usr/bin/env python3
"""Busca vagas de edição de vídeo em fontes com API aberta, filtra e (opcional) classifica com IA.
Saída: vagas.json (lido pelo painel). Sem dependências externas."""
import json, os, re, sys, urllib.request, urllib.parse, datetime

HOJE = datetime.date.today().isoformat()
ARQ = "vagas.json"
MANTER_DIAS = 30
MODELO = os.environ.get("MODELO_IA", "claude-haiku-5-5")
CHAVE = os.environ.get("ANTHROPIC_API_KEY", "")

PALAVRAS = re.compile(r"video edit|vídeo|video|editor de v|premiere|after effects|davinci|motion graphic|shorts|reels|videomaker|youtube", re.I)
TITULO_OK = re.compile(r"edit|motion|video|vídeo|videomaker|animator|animação", re.I)
BR = re.compile(r"brasil|brazil|latam|latin america|south america|américa latina", re.I)
ABERTA = re.compile(r"worldwide|anywhere|global|remote|latam|latin america|brazil|brasil|^$", re.I)
SO_FORA = re.compile(r"\b(us|usa|u\.s\.|united states|uk|europe|eu|canada|australia)\b.*\b(only|based|residents)\b|\bonly\b.*\b(us|usa|uk|europe|canada)\b", re.I)

def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "painel-vagas-pessoal/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def limpar(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()

def remotive():
    d = baixar("https://remotive.com/api/remote-jobs?search=" + urllib.parse.quote("video editor"))
    for j in d.get("jobs", []):
        yield dict(id=f"remotive-{j['id']}", titulo=j["title"], empresa=j["company_name"], url=j["url"],
                   fonte="Remotive", local=j.get("candidate_required_location", ""), pagamento=j.get("salary", ""),
                   data=(j.get("publication_date") or "")[:10], texto=limpar(j.get("description"))[:1500])

def remoteok():
    d = baixar("https://remoteok.com/api")
    for j in d[1:]:
        if not isinstance(j, dict): continue
        pg = ""
        if j.get("salary_min"): pg = f"US$ {j['salary_min']}-{j.get('salary_max','')} /ano"
        yield dict(id=f"remoteok-{j['id']}", titulo=j.get("position", ""), empresa=j.get("company", ""), url=j.get("url", ""),
                   fonte="RemoteOK", local=j.get("location", ""), pagamento=pg,
                   data=(j.get("date") or "")[:10], texto=limpar(j.get("description"))[:1500] + " " + " ".join(j.get("tags", [])))

def jobicy():
    d = baixar("https://jobicy.com/api/v2/remote-jobs?count=50&tag=" + urllib.parse.quote("video editor"))
    for j in d.get("jobs", []):
        pg = ""
        if j.get("annualSalaryMin"): pg = f"{j.get('salaryCurrency','')} {j['annualSalaryMin']}-{j.get('annualSalaryMax','')} /ano"
        geo = j.get("jobGeo", "")
        yield dict(id=f"jobicy-{j['id']}", titulo=j.get("jobTitle", ""), empresa=j.get("companyName", ""), url=j.get("url", ""),
                   fonte="Jobicy", local=geo if isinstance(geo, str) else ", ".join(geo), pagamento=pg,
                   data=(j.get("pubDate") or "")[:10], texto=limpar(j.get("jobExcerpt"))[:1500])

# Para somar fontes, crie uma função parecida e coloque aqui.
FONTES = [remotive, remoteok, jobicy]

def heuristica(v):
    if not TITULO_OK.search(v["titulo"]) or not PALAVRAS.search(v["titulo"] + " " + v["texto"]): return False
    if SO_FORA.search(v["local"]) and not BR.search(v["local"]): return False
    return bool(ABERTA.search(v["local"]) or BR.search(v["local"]))

def ia(lote):
    """Pede à IA: serve pra editor de vídeo? aberta a quem mora no Brasil? quanto paga? nicho?"""
    itens = [{"id": v["id"], "titulo": v["titulo"], "local": v["local"], "pagamento": v["pagamento"], "texto": v["texto"][:700]} for v in lote]
    prompt = ("Você filtra vagas para um editor de vídeo brasileiro. Para cada vaga responda com JSON puro, sem texto extra: "
              '[{"id":"...","serve":true/false,"brasil_ok":true/false,"pagamento":"texto curto ou vazio","nicho":"ex.: games, finanças, shorts, geral","resumo":"1 frase"}]. '
              "serve=false se não for edição de vídeo/motion, for spam, ou exigir muito além de edição. "
              "brasil_ok=false se exigir morar em outro país ou fuso incompatível. Vagas:\n" + json.dumps(itens, ensure_ascii=False))
    corpo = json.dumps({"model": MODELO, "max_tokens": 3000, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=corpo, method="POST",
        headers={"x-api-key": CHAVE, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = json.loads(r.read())["content"][0]["text"]
    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
    return {x["id"]: x for x in json.loads(txt)}

def main():
    antigas = {}
    if os.path.exists(ARQ):
        try:
            antigas = {v["id"]: v for v in json.load(open(ARQ, encoding="utf-8")).get("vagas", [])}
        except Exception: pass
    achadas = {}
    for f in FONTES:
        try:
            for v in f():
                if heuristica(v): achadas[v["id"]] = v
            print("ok", f.__name__)
        except Exception as e:
            print("FALHOU", f.__name__, e, file=sys.stderr)
    novas = [v for i, v in achadas.items() if i not in antigas]
    print(len(achadas), "passaram no filtro;", len(novas), "novas")
    veredito = {}
    if CHAVE and novas:
        for k in range(0, len(novas), 15):
            try: veredito.update(ia(novas[k:k+15]))
            except Exception as e: print("IA falhou:", e, file=sys.stderr)
    for v in novas:
        a = veredito.get(v["id"])
        if a and (not a.get("serve") or not a.get("brasil_ok")): continue
        v["regiao"] = "br" if BR.search(v["local"]) else "ex"
        v["primeira_vez"] = HOJE
        if a:
            v["pagamento"] = a.get("pagamento") or v["pagamento"]
            v["nicho"] = a.get("nicho", ""); v["resumo"] = a.get("resumo", "")
        antigas[v["id"]] = v
    limite = (datetime.date.today() - datetime.timedelta(days=MANTER_DIAS)).isoformat()
    final = [v for v in antigas.values() if v.get("primeira_vez", HOJE) >= limite]
    for v in final: v["novo"] = v.get("primeira_vez") == HOJE; v.pop("texto", None)
    final.sort(key=lambda v: (v.get("primeira_vez", ""), v.get("data", "")), reverse=True)
    json.dump({"atualizado": HOJE, "vagas": final}, open(ARQ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("salvo", len(final))

if __name__ == "__main__": main()
