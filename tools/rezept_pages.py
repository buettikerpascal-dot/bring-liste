# Erzeugt pro Gericht eine Bring-Seite rezept-<woche>-<id>.html aus dem Cockpit-HTML.
# Aufruf: python3 tools/rezept_pages.py <cockpit.html> <repo-ordner>  -> schreibt Seiten und week_bring.json (week-Block mit Feld bring)
import json,re,html,sys
src,repo=sys.argv[1],sys.argv[2]
h=open(src).read()
get=lambda id: json.loads(re.search(r'<script type="application/json" id="%s">(.*?)</script>'%id,h,re.S).group(1).replace('<\\/','</'))
W=get('week'); S=get('state'); leer=S.get('vorratLeer',{})
def fq(q):
    try:
        f=float(q); return str(int(f)) if f==int(f) else str(round(f,1))
    except: return q
made=[]
for w in W['weeks']:
    for m in w['meals']:
        items=[]
        for g in m['ingredients']:
            if g.get('dept')=='Reste': continue
            if g.get('dept')=='Vorrat' and not leer.get(g.get('vorrat') or g['name']): continue
            q=g['qty']
            if g['unit'] in ('Stück','Bund','Zehe','Zehen','Dose','Glas','kleines Glas','Packung'):
                try:
                    import math; q=str(math.ceil(float(q)-1e-9))
                except: pass
            items.append(f"{fq(q)} {g['unit']} {g['name']}".strip())
        if not items:
            m.pop('bring',None); continue
        page=f"rezept-{w['id']}-{m['id']}.html"
        ld={"@context":"https://schema.org","@type":"Recipe","name":m['title'],"author":{"@type":"Person","name":"Familie"},"recipeYield":str(m['persons']),"recipeIngredient":items,"recipeInstructions":"Zutaten für dieses Gericht."}
        body="".join(f'<li itemprop="recipeIngredient">{html.escape(i)}</li>\n' for i in items)
        doc=f'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(m['title'])}</title>
<script type="application/ld+json">
{json.dumps(ld,ensure_ascii=False,indent=1)}
</script>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:24px 16px;background:#121417;color:#F2F4F5}}li{{padding:6px 0;border-bottom:1px solid #2A2F36}}ul{{list-style:none;padding:0}}</style>
</head>
<body itemscope itemtype="http://schema.org/Recipe">
<h1 itemprop="name">{html.escape(m['title'])}</h1>
<p>Von <span itemprop="author">Familie</span> · für <span itemprop="recipeYield">{m['persons']}</span></p>
<ul>
{body}</ul>
</body>
</html>
'''
        open(f"{repo}/{page}","w").write(doc)
        m['bring']={"page":page,"base":m['persons'],"n":len(items)}
        made.append(page)
json.dump(W,open('week_bring.json','w'),ensure_ascii=False)
print(len(made),made)
