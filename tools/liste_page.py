# Erzeugt eine Bring-Wochenliste (nur Artikel) aus dem Cockpit-HTML.
# Aufruf: python3 tools/liste_page.py <cockpit.html> <wochen-id> <shopping|shopping2> <ziel.html>
import json,re,html,sys
src,wid,key,out=sys.argv[1:5]
h=open(src).read()
W=json.loads(re.search(r'<script type="application/json" id="week">(.*?)</script>',h,re.S).group(1).replace('<\\/','</'))
w=[x for x in W['weeks'] if x['id']==wid][0]
items=[f"{s['qty']} {s['name']}" for s in w[key]]
ld={"@context":"https://schema.org","@type":"Recipe","name":"Einkaufsliste","author":{"@type":"Person","name":"Familie"},"recipeYield":"4","recipeIngredient":items,"recipeInstructions":"Einkaufsliste."}
lis="".join(f'<li itemprop="recipeIngredient">{html.escape(i)}</li>\n' for i in items)
open(out,"w").write(f'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Einkaufsliste</title>
<script type="application/ld+json">
{json.dumps(ld,ensure_ascii=False,indent=1)}
</script>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:24px 16px;background:#121417;color:#F2F4F5}}li{{padding:6px 0;border-bottom:1px solid #2A2F36}}ul{{list-style:none;padding:0}}</style>
</head>
<body itemscope itemtype="http://schema.org/Recipe">
<h1 itemprop="name">Einkaufsliste</h1>
<p>Von <span itemprop="author">Familie</span></p>
<ul>
{lis}</ul>
</body>
</html>
''')
print(len(items),out)
