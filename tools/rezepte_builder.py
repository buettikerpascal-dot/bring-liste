# Rezept-Builder für das Ernährungs-Cockpit (Rezept-Modell ab 05.11.2026).
# Aufruf: python3 tools/rezepte_builder.py <spec.py> <live-cockpit.html> <out.html>
#   - liest die Rezept-Spezifikation (Format unten), rechnet Familienmengen für 6 Portionen und Pascals Portion (Mittag/Abend),
#   - ersetzt im Live-HTML NUR den JSON-Block id="week" (state bleibt unverändert),
#   - erzeugt die Bring-Seiten mit tools/rezept_pages2.py im Repository und trägt die bring-Felder ein.
#
# spec.py:
#   WEEK = {'id': 'kw46', 'week': 'KW 46', 'label': 'ab Sa 7.11.', 'from': '2026-11-07', 'to': '2026-11-13'}
#   V, G, F, K, T, C, N = 'Vorrat', 'Gemüse & Früchte', 'Fleisch & Fisch', 'Kühlregal', 'Getreide & Teigwaren', 'Konserven & Saucen', 'Nüsse & Kerne'
#   recipes = [
#     dict(id='k46a1',   # eindeutig über alle Wochen (Bewertungen hängen an der id)
#           title='…', minutes=30, protein='Rind', carb='Reis',
#          # (Zutat, Menge Pascal, Menge je Elternteil, Einheit, Abteilung[, Vorrat-Knopf])  -> für EINE Mahlzeit zu dritt
#          ing=[('Basmatireis', (103, 92), 70, 'g', V, 'Basmatireis'), ('Rindsgeschnetzeltes', (131, 131), 120, 'g', F), ('Zwiebel', 1, 0, 'Stück', V, 'Zwiebeln')],
#          steps=['…'], p=lambda: pascal('Mittag', 'Reis', 'Rind', 'Rindsgeschnetzeltes', 'Olivenöl', 'über deinen Reis'),
#          keep=None,            # None = automatisch aus der Eiweissquelle; sonst Text
#          fresh2=None,          # None = automatisch (frischer Fisch, Spiegelei, Rösti); True = zweimal frisch kochen
#          steps2=None, freshNote=None, note=None, inspo=False, inspoId=None, carried=False,  # carried=True: aus der Vorwoche übernommen
#          source='https://…', sourceTitle='…', sourceSite='…'),
#   ]
# Familienmenge für 6 Portionen (Entscheid Pascal 07.11.2026) = Pascals Planmenge Mittag + Abend + 4 × Normalportion je Elternteil.
#   Eiweiss und Kohlenhydrat: Menge Pascal als Tupel (Mittag, Abend), z.B. ('Basmatireis', (103, 92), 70, 'g', V, 'Basmatireis').
#   Menge je Elternteil = normale Rezeptportion, NICHT mehr als Pascal (Richtwerte NORMAL unten).
#   Feste Mengen (Zwiebel, Gewürz, Öl) stehen bei Pascal als Zahl für das Gericht einer Mahlzeit und werden verdoppelt.
#   Gemüse total ca. 200 g pro Portion (also ca. 1200 g für 6), als feste Menge.
NORMAL = {  # Richtwerte Normalportion pro Person und Mahlzeit, roh
 'Poulet': 120, 'Rind': 120, 'Schwein': 120, 'Fisch': 120, 'Lachs': 120, 'Hackfleisch': 100, 'Thunfisch (abgetropft)': 80,
 'Tofu': 120, 'Eier (Stück)': 2, 'Kartoffeln': 200, 'Reis': 70, 'Couscous': 70, 'Quinoa': 70, 'Polenta': 70, 'Ebly': 70,
 'Pasta': 80, 'Gnocchi': 200, 'Rösti': 200, 'Spätzli': 150, 'Vollkornbrot': 100, 'Gemüse total': 200}
import json, math, os, re, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
KH = {  # (Mittag, Abend): Planmenge g, kcal, P, KH, F
 'Kartoffeln': ((506, 370, 10, 79, 1), (451, 330, 9, 70, 0)),
 'Pasta': ((101, 370, 13, 70, 3), (90, 330, 12, 63, 3)),
 'Reis': ((103, 370, 8, 81, 1), (92, 330, 7, 72, 1)),
 'Quinoa': ((102, 370, 15, 64, 5), (91, 330, 13, 57, 5)),
 'Couscous': ((109, 370, 13, 73, 2), (97, 330, 12, 65, 2)),
 'Ebly': ((105, 370, 13, 74, 1), (94, 330, 11, 66, 1)),
 'Polenta': ((106, 370, 9, 78, 1), (95, 330, 8, 70, 1)),
 'Gnocchi': ((230, 370, 9, 70, 5), (205, 330, 8, 62, 5)),
 'Rösti': ((312, 370, 6, 58, 12), (279, 330, 6, 52, 10)),
 'Vollkornbrot': ((181, 370, 13, 66, 4), (161, 330, 12, 59, 4)),
 'Spätzli': ((242, 370, 13, 70, 4), (216, 330, 12, 62, 4)),
}
EW = {  # Planmenge g, kcal, P, KH, F
 'Poulet': (163, 180, 40, 0, 2), 'Rind': (131, 180, 30, 0, 6), 'Lachs': (96, 180, 19, 0, 11),
 'Thunfisch': (117, 180, 27, 0, 7), 'Ei': (128, 180, 15, 2, 12), 'Tofu': (130, 180, 19, 1, 10),
 'Kichererbsen': (148, 180, 11, 26, 3), 'Linsen': (60, 180, 15, 27, 1), 'Seitan': (123, 180, 30, 5, 3),
 'Quorn': (239, 180, 26, 8, 5),
}
FETT = {'Olivenöl': (0, 0, 22), 'Leinöl': (0, 0, 21), 'Avocado': (3, 1, 20), 'Nüsse': (5, 4, 18)}
TOPPING_G = {'Olivenöl': 17, 'Leinöl': 16, 'Avocado': 98, 'Nüsse': 21}
GEMUESE = (30, 2, 5, 0)
FACTOR = {'Reis': (2.6, 'gekocht'), 'Pasta': (2.2, 'gekocht'), 'Quinoa': (2.7, 'gekocht'), 'Couscous': (2.3, 'gequollen'),
 'Ebly': (2.5, 'gekocht'), 'Polenta': (4.0, 'gekocht'), 'Gnocchi': (1.0, 'gekocht, Gewicht bleibt etwa gleich'),
 'Rösti': (1.0, 'gebraten, Gewicht bleibt etwa gleich'), 'Kartoffeln': (0.85, 'gegart'), 'Poulet': (0.75, 'gebraten'),
 'Rind': (0.72, 'gebraten'), 'Lachs': (0.8, 'gebacken'), 'Tofu': (0.9, 'gebraten'), 'Linsen': (2.3, 'gekocht'),
 'Vollkornbrot': (1.0, 'gleich, getoastet'), 'Spätzli': (1.0, 'gebraten, Gewicht bleibt etwa gleich'),
 'Seitan': (0.9, 'gebraten'), 'Quorn': (0.9, 'gebraten')}
P_KH_NAME = {'Kartoffeln': 'Kartoffeln', 'Pasta': 'Vollkornpasta', 'Reis': 'Reis', 'Quinoa': 'Quinoa', 'Couscous': 'Couscous',
 'Ebly': 'Ebly', 'Polenta': 'Schnellkoch-Polenta', 'Gnocchi': 'Gnocchi', 'Rösti': 'Rösti', 'Vollkornbrot': 'Vollkornbrot', 'Spätzli': 'Spätzli'}
def cooked(food, g):
    if food in ('Thunfisch', 'Kichererbsen', 'Ei'): return 'Gewicht bleibt gleich'
    f, word = FACTOR[food]
    if f == 1.0: return word
    return f'{word} ≈ {round(g * f)} g'
def pascal(slot, kh, ew, ew_name, fett, fett_hint, alone=False, ew_note=None):
    mi = 0 if slot == 'Mittag' else 1
    khg, kc, p, k, f = KH[kh][mi]; eg, ekc, ep, ek, ef = EW[ew]
    items = [{'name': P_KH_NAME[kh], 'raw': f'{khg} g', 'cooked': cooked(kh, khg)},
             {'name': ew_name, 'raw': ew_note or f'{eg} g', 'cooked': cooked(ew, eg)},
             {'name': 'Gemüse aus dem Gericht', 'raw': '130 g+', 'cooked': 'Menge frei'}]
    tot = [kc + ekc + GEMUESE[0], p + ep + GEMUESE[1], k + ek + GEMUESE[2], f + ef]
    if alone:
        items.append({'name': 'Olivenöl', 'raw': '24 g', 'cooked': 'ganzer Fettbaustein, zum Kochen und darüber'})
        tot = [tot[0] + 200, tot[1], tot[2], tot[3] + 22]
    else:
        items.append({'name': fett if fett != 'Nüsse' else fett_hint.split(' ')[0], 'raw': f'{TOPPING_G[fett]} g', 'cooked': fett_hint})
        tp, tk, tf = FETT[fett]
        tot = [tot[0] + 200, tot[1] + 0.7 * tp, tot[2] + 0.7 * tk, tot[3] + 6.6 + 0.7 * tf]
    return items, {'kcal': round(tot[0]), 'p': round(tot[1]), 'kh': round(tot[2]), 'f': round(tot[3])}
FRESH_PROTEIN = ('Lachs', 'Fisch', 'Forelle', 'Egli', 'Zander', 'Kabeljau', 'Dorsch', 'Felchen', 'Saibling', 'Crevetten', 'Pangasius', 'Seelachs')
def is_fresh(r, fam):
    txt = ' '.join([r['title'], r['protein']] + [g['name'] for g in fam if g['dept'] == 'Fleisch & Fisch'] + r['steps']).lower()
    if 'spiegelei' in txt or r['carb'] == 'Rösti': return True
    return any(f.lower() in txt for f in FRESH_PROTEIN) and 'thunfisch' not in r['protein'].lower()
def fmt(q): return str(int(q)) if abs(q - round(q)) < 1e-9 else str(round(q, 1)).rstrip('0').rstrip('.')
def build_recipe(r, env):
    fam = []
    for t in r['ing']:
        name, pq, eq, unit, dept = t[:5]; vor = t[5] if len(t) > 5 else None
        if vor and vor not in env.get('VORRAT_LIST', []): sys.exit(f'Unbekannter Vorrat-Knopf {vor!r} bei {name}: erlaubt sind {env.get("VORRAT_LIST")}')
        # pq als (Mittag, Abend): Pascals zwei Planportionen; sonst feste Menge für das Gericht einer Mahlzeit (×2)
        q = (pq[0] + pq[1] if isinstance(pq, (tuple, list)) else 2 * pq) + 4 * eq
        if unit in ('Stück', 'Bund', 'Zehen', 'Zehe', 'Dose', 'Glas', 'Packung', 'Stange'): q = math.ceil(q - 1e-9)
        fam.append({'name': name, 'qty': fmt(q), 'unit': unit, 'dept': dept, 'vorrat': vor})
    orig = env['pascal']; pby = {}
    for sl in ('Mittag', 'Abend'):
        env['pascal'] = (lambda s, *a, _sl=sl, **k: orig(_sl, *a, **k)); it, mc = r['p'](); pby[sl] = {'pascal': it, 'macros': mc}
    env['pascal'] = orig
    fresh = r.get('fresh2')
    if fresh is None: fresh = is_fresh(r, fam)
    keep = r.get('keep') or ('zweimal frisch kochen' if fresh else ('Reste nur am nächsten Tag' if r['protein'] == 'Poulet' or 'hack' in r['title'].lower() or any('hack' in g['name'].lower() for g in fam) else 'Reste bis 2 Tage'))
    out = {'id': r['id'], 'title': r['title'], 'minutes': r['minutes'], 'protein': r['protein'], 'carb': r['carb'], 'portions': 6,
           'keep': keep, 'ingredients': fam, 'steps': r['steps'], 'pby': pby}
    if fresh: out['fresh2'] = True
    for k in ('steps2', 'freshNote', 'note', 'inspo', 'inspoId', 'carried', 'source', 'sourceTitle', 'sourceSite', 'forWho'):
        if r.get(k): out[k] = r[k]
    return out
def main(spec, live, outp):
    H = open(live).read()
    blk = lambda id: re.search(r'(<script type="application/json" id="%s">)(.*?)(</script>)' % id, H, re.S)
    old = json.loads(blk('week').group(2).replace('<\\/', '</'))
    if 'recipes' not in old: sys.exit('Live-Cockpit ist noch im alten Wochenplan-Format: zuerst das Rezept-Template einspielen.')
    env = dict(globals()); env['VORRAT_LIST'] = old.get('vorrat', []); exec(open(spec).read(), env)
    # Verlauf: frühere Rezepte (id, Titel, Woche, Eiweiss, Kohlenhydrat, gekocht) für Bewertungen und Wiederholungs-Regel, max. 60 Einträge
    st = json.loads(blk('state').group(2).replace('\\u003c', '<'))
    hist = old.get('history', []) + [{'id': r['id'], 'title': r['title'], 'week': old['week'].get('week'), 'protein': r.get('protein'), 'carb': r.get('carb'),
            'cooked': bool(st.get('gekocht', {}).get(r['id'])), 'carried': bool(r.get('carried'))} for r in old.get('recipes', [])]
    seen = set(); hist = [h for h in hist if not (h['id'] in seen or seen.add(h['id']))][-60:]
    D = {'week': env['WEEK'], 'recipes': [build_recipe(r, env) for r in env['recipes']], 'vorrat': old.get('vorrat', []), 'history': hist}
    ids = [r['id'] for r in D['recipes']]
    if len(set(ids)) != len(ids) or set(ids) & {h['id'] for h in hist}: sys.exit('Rezept-ids müssen eindeutig sein und dürfen im Verlauf nicht vorkommen (z.B. k46a1).')
    def put(Hs, D):
        wj = json.dumps(D, ensure_ascii=False).replace('</', '<\\/')
        return re.sub(r'(<script type="application/json" id="week">).*?(</script>)', lambda m: m.group(1) + wj + m.group(2), Hs, count=1, flags=re.S)
    tmp = outp + '.tmp.html'; open(tmp, 'w').write(put(H, D))
    j = outp + '.bring.json'
    subprocess.run([sys.executable, os.path.join(HERE, 'rezept_pages2.py'), tmp, REPO, j], check=True)
    D = json.load(open(j)); open(outp, 'w').write(put(H, D)); os.remove(tmp)
    print('ok', len(D['recipes']), 'Rezepte ->', outp)
if __name__ == '__main__': main(*sys.argv[1:4])
