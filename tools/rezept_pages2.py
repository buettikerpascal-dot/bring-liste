# Rezept-Modell (ab 05.11.2026): erzeugt pro Rezept zwei Bring-Seiten aus dem Cockpit-HTML.
#   rezept-<woche>-<id>.html    alle Zutaten ausser Grundvorrat (dept "Vorrat")
#   rezept-<woche>-<id>-v.html  zusätzlich die Vorrat-Zutaten, die einem Knopf im Reiter «Vorrat» entsprechen
# Das Cockpit nimmt die -v-Seite, sobald eine Vorrat-Zutat des Rezepts im Reiter «Vorrat» als leer markiert ist.
# Aufruf: python3 tools/rezept_pages2.py <cockpit.html> <repo-ordner> [<out.json>]
#   -> schreibt die Seiten und <out.json> (week-Block mit Feld bring pro Rezept)
import json,re,html,sys,math
src,repo=sys.argv[1],sys.argv[2]
out=sys.argv[3] if len(sys.argv)>3 else 'week_bring.json'
h=open(src).read()
get=lambda id: json.loads(re.search(r'<script type="application/json" id="%s">(.*?)</script>'%id,h,re.S).group(1).replace('<\\/','</'))
D=get('week')
COUNT=('Stück','Bund','Zehe','Zehen','Dose','Dosen','Glas','kleines Glas','Packung','Stange','Stangen')
def fq(q,unit):
    try:
        f=float(q)
        if unit in COUNT: f=math.ceil(f-1e-9)
        return str(int(f)) if f==int(f) else str(round(f,1))
    except: return str(q)
def page(r,items,name):
    ld={"@context":"https://schema.org","@type":"Recipe","name":r['title'],"author":{"@type":"Person","name":"Familie"},"recipeYield":str(r['portions']),"recipeIngredient":items,"recipeInstructions":"Zutaten für dieses Rezept."}
    body="".join(f'<li itemprop="recipeIngredient">{html.escape(i)}</li>\n' for i in items)
    open(f"{repo}/{name}","w").write(f'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(r['title'])}</title>
<script type="application/ld+json">
{json.dumps(ld,ensure_ascii=False,indent=1)}
</script>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:24px 16px;background:#0B1020;color:#F1F5F9}}li{{padding:6px 0;border-bottom:1px solid #26304A}}ul{{list-style:none;padding:0}}</style>
</head>
<body itemscope itemtype="http://schema.org/Recipe">
<h1 itemprop="name">{html.escape(r['title'])}</h1>
<p>Von <span itemprop="author">Familie</span> · für <span itemprop="recipeYield">{r['portions']}</span></p>
<ul>
{body}</ul>
</body>
</html>
''')
VORRAT=D.get('vorrat',[])
def vkeys(g):
    # gleiche Zuordnung wie im Cockpit: Feld vorrat, sonst Namensvergleich mit der Vorratsliste
    if g.get('vorrat'): return [g['vorrat']]
    n=g['name'].lower()
    return [v for v in VORRAT if v.lower() in n or n in v.lower()]
made=[]
wid=D['week']['id']
for r in D['recipes']:
    base=[];allv=[]
    for g in r['ingredients']:
        if g.get('dept')=='Reste': continue
        it=f"{fq(g['qty'],g['unit'])} {g['unit']} {g['name']}".strip()
        if g.get('dept')!='Vorrat': base.append(it); allv.append(it)
        elif vkeys(g): allv.append(it)
    b={}
    if base:
        b['page']=f"rezept-{wid}-{r['id']}.html"; page(r,base,b['page']); made.append(b['page'])
    if len(allv)>len(base):
        b['pageV']=f"rezept-{wid}-{r['id']}-v.html"; page(r,allv,b['pageV']); made.append(b['pageV'])
        if 'page' not in b: b['page']=b['pageV']
    # pro Vorrat-Knopf eine eigene Seite (Rezept + nur diese Vorrat-Zutat), wird genommen, wenn genau dieser Vorrat leer ist
    keys=[]
    for g in r['ingredients']:
        if g.get('dept')=='Vorrat':
            for k in vkeys(g):
                if k not in keys: keys.append(k)
    if base and keys:
        b['pageVK']={}
        for k in keys:
            its=base+[f"{fq(g['qty'],g['unit'])} {g['unit']} {g['name']}".strip() for g in r['ingredients'] if g.get('dept')=='Vorrat' and k in vkeys(g)]
            slug=re.sub(r'[^a-z0-9]+','-',k.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue')).strip('-')
            nm=f"rezept-{wid}-{r['id']}-v-{slug}.html"; page(r,its,nm); made.append(nm); b['pageVK'][k]=nm
    if b: r['bring']=b
    else: r.pop('bring',None)
json.dump(D,open(out,'w'),ensure_ascii=False)
print(len(made),made)
