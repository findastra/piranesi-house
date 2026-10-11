"""The 7x7 House: where everything sits in the world (Unity x right, z north; metres). Shared by the layout and the
explainer page. The labyrinth itself comes from maze/final.json."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
MAZE = json.load(open(os.path.join(HERE, '..', 'maze', 'final.json')))
N = MAZE['N']; G = 60.0; HALF = (N // 2) * G + 12.0          # 192 m: the outer faces of the outer halls
def cell_pos(c): return [(c[0] - N // 2) * G, 0.0, (c[1] - N // 2) * G]
EXITS = {e['name']: e for e in MAZE['exits']}
def ex(n): return EXITS[n]['cell']
# islands and buildings beyond each exit (centre x, z; radii; crest; interior; seed; rotation)
_sg = cell_pos(ex('Sea Gate')); _eg = cell_pos(ex('East Water Stair')); _td = cell_pos(ex('Tower Door')); _aq = cell_pos(ex('Aqueduct Arch'))
CASCADE = ((ex('Aqueduct Arch')[0] + 1, N - 1), 'N') if ex('Aqueduct Arch')[0] + 1 < N else ((ex('Aqueduct Arch')[0] - 1, N - 1), 'N')
_cs = cell_pos(CASCADE[0])
ISLANDS = [
    ('Isle_SouthBeach', (_td[0], -HALF - 58.0), (58.0, 22.0), 1.4, 2.6, 1),
    ('Isle_Ruin', (HALF + 92.0, _eg[2]), (48.0, 34.0), 1.2, 2.2, 2),      # spawn isle: its beach meets the East Water Stair
    ('Isle_Albatross', (-HALF - 36.0, HALF + 36.0), (19.0, 16.0), 1.0, 2.2, 3),
    ('Isle_Pump', (_aq[0] + 12.0, HALF + 46.0), (52.0, 13.0), 0.8, 1.6, 4),    # straight out from the Aqueduct Arch, its east tip by the noria
    ('Isle_TowerShoal', (_td[0], -HALF - 24.0), (11.0, 6.0), 0.95, 1.25, 11),
    ('Isle_CornerBar', (HALF + 14.0, -HALF - 14.0), (15.0, 7.5), 0.95, 1.3, 12, -45.0),
    ('Isle_West', (-HALF - 105.0, _sg[2]), (34.0, 24.0), 1.1, 2.0, 13),
    ('Isle_Causeway', (HALF + 30.0, _eg[2]), (18.0, 7.0), -0.1, 0.12, 14),   # tidal sand spit from the East Water Stair to the Ruin isle
]
WRECK = (-HALF - 70.0, -HALF + 20.0)
CORNER_HALL = dict(entrance=(HALF + 28.5, -HALF - 28.5), ry=135.0)     # the hall on Corner Isle (was 'the Sea Hall')
DOLPHINS = [dict(a=[-HALF - 60, 0, -HALF - 60], b=[-HALF - 60, 0, HALF + 40]), dict(a=[HALF + 150, 0, -HALF - 60], b=[HALF + 150, 0, -40]),
            dict(a=[-HALF - 80, 0, -HALF - 55], b=[HALF + 60, 0, -HALF - 55])]

# the colour key: one neon colour per road, shared by the world (glowing pedestal rings, roof tubes) and the key website
FAMILY_COLORS = {'Elephant': '#3d8bff', 'Gorilla': '#ff5a36', 'Boy with Cymbals': '#a45bff', 'Angel': '#ffb21f', 'Minotaur': '#2ee88a', 'Albatross': '#ff4fa8'}
FAMILY_COLORS_INK = {'Elephant': '#1f5fd0', 'Gorilla': '#d23c1a', 'Boy with Cymbals': '#7a36d8', 'Angel': '#b87800', 'Minotaur': '#0f9256', 'Albatross': '#cc2a80'}
FAMILY_BOOK = {'Elephant': 'the Elephant Carrying a Castle', 'Gorilla': 'the Gorilla', 'Boy with Cymbals': 'the Boy Playing the Cymbals',
               'Angel': 'the Angel caught in a rose bush', 'Minotaur': 'the Minotaurs', 'Albatross': 'the Albatross'}
def rgb(h): return [round(int(h[i:i + 2], 16) / 255.0, 4) for i in (1, 3, 5)]

# the Far Hall Quests: one prize in each far hall, matching the lesson of the road that leads there
QUESTS = [
    dict(exit='Sea Gate', hall='The Drowned Halls', prize="A page of Piranesi's journal", role='Rememberer',
         lesson='Memory: what is written down is never wholly lost.', how='On a lectern above the water at the far end of the Drowned Halls.'),
    dict(exit='East Water Stair', hall='The Derelict Halls', prize='A gold-mended shard', role='Mender',
         lesson='Broken things can still hold beauty, and from the top of the ruin you see the whole.', how='At the top of the rubble climb, on the broken upper floor.'),
    dict(exit='Tower Door', hall='The Ninth Vestibule', prize='Golden honeycomb', role='Beekeeper',
         lesson='Joy and togetherness: three tides join, and bees build as one.', how="On the landing at the feet of the Woman Carrying a Beehive."),
    dict(exit='Aqueduct Arch', hall='The Upper Halls', prize='A cloud in a jar', role='Cloud-Walker',
         lesson='Hope: even caught, you can rise above the storm.', how='On the platform above the cloud, at the top of the stair through it.'),
    dict(exit='Corner Passage', hall='The Hall of the Minotaurs', prize="Ariadne's golden thread", role='Thread-Bearer',
         lesson='Courage: what looks monstrous can be gentle, and the way home is never lost.', how="At the Faun's feet. Take it and a gold thread lights the floors of the labyrinth, leading home to the Colossus."),
    dict(exit='Bird Stair', hall='The Alcove of the Dead', prize='A candle lit for you', role='Keeper of the Dead',
         lesson='Kindness that asks nothing back.', how='Leave a water lily on the offering plinth; a candle is lit and stays burning.'),
]
# why each road has its statue (shown on the key website)
FAMILY_WHY = {
    'Elephant': "The Elephant Carrying a Castle is one of the House's statues in the book. Elephants are said never to forget, and this one carries its castle, its home, on its back. Its road leaves by the Sea Gate, crosses to West Isle and wades on to the Drowned Halls, where the sea keeps the memory of every hall it has filled; the prize there is a page of Piranesi's journal, the way he keeps his own memory.",
    'Gorilla': "The Gorilla is one of the House's statues in the book; here it stands for strength that is calm and patient. It is the first family you meet, at the East Water Stair where you arrive. Its road crosses the tidal Causeway to Ruin Isle, where people stuck here have made a home, and wades on to the Derelict Halls, where that kind of strength is what gets you up through the ruin.",
    'Boy with Cymbals': "The Boy Playing the Cymbals is one of the House's statues in the book. A crash of cymbals is the sound of things meeting in joy. His road leaves by the Tower Door, past the Marble Tower and its slide on Tower Shoal and the hammock on Beach Isle, to the Ninth Vestibule, where three tides crash together and the Woman Carrying a Beehive stands for work shared and made sweet.",
    'Angel': "The Angel caught in a rose bush is one of the House's statues in the book. It is held fast by something beautiful, as Piranesi is held by the House, and it still has wings. Its road leaves under the Aqueduct Arch, past the noria and the Pump House on Pump Isle that lift the sea up into the House, and on up to the Upper Halls and the clouds, the part of the House closest to the sky.",
    'Minotaur': "The House has a hall of eight great Minotaurs. The monster at the heart of every labyrinth is, in the House, a statue, not a monster. Its road leaves by the Corner Passage, past the Corner Hall standing in the sea, to the Hall of the Minotaurs, where the prize is Ariadne's thread: courage, and the way home.",
    'Albatross': "In the book Piranesi dates a year by the Albatross coming to the House, and sailors held that albatrosses carry the souls of those lost at sea. Its road climbs the Bird Stair to Albatross Isle, past its giant egg in the marble nest on top of the Bird Tower, new life, and on to the Alcove of the Dead, where the lesson is kindness to those who are gone.",
}

# where you arrive: the camp on the terrace of the East Water Stair, facing the way in; Ruin Isle (to rest first) behind
SPAWN = dict(p=[HALF + 7.5, 0.1, _eg[2]], r=270.0, where='the camp on the terrace of the East Water Stair, facing the way in')

# the six roads out, each one straight line in its own colour: gate -> (stepping sand) -> isle and its building -> far bar ->
# far hall (with its far wing behind). One name per place, used by the world, the plaques' roles and the key website.
# Kinds of sand: an 'Isle' has a building; a 'Shoal' or 'Causeway' is a small stepping sand; a 'Bar' carries a far wing.
CHAINS = [
    dict(exit='Sea Gate', family='Elephant', wind='west', isle='Isle_West', isle_name='West Isle', building='West Isle Hall',
         step=None, bar_name='Drowned Bar', hall='The Drowned Halls',
         sights='the sunken broken stair, West Isle Hall, the wreck to the south'),
    dict(exit='East Water Stair', family='Gorilla', wind='east', isle='Isle_Ruin', isle_name='Ruin Isle', building='the Lived-in Hall',
         step=('Isle_Causeway', 'the Causeway'), bar_name='Derelict Bar', hall='The Derelict Halls',
         sights='the spawn camp on the stair terrace, the tidal Causeway, the ruin and its fruit table, the vine pergolas, the Lived-in Hall'),
    dict(exit='Tower Door', family='Boy with Cymbals', wind='south', isle='Isle_SouthBeach', isle_name='Beach Isle', building='Beach Isle Hall',
         step=('Isle_TowerShoal', 'Tower Shoal'), bar_name='Vestibule Bar', hall='The Ninth Vestibule',
         sights='the Marble Tower and its slide (on Tower Shoal), the hammock, the dock and gondola, Beach Isle Hall'),
    dict(exit='Aqueduct Arch', family='Angel', wind='north', isle='Isle_Pump', isle_name='Pump Isle', building='the Pump House',
         step=None, bar_name='Upper Bar', hall='The Upper Halls',
         sights='the sunken broken stair, the aqueduct and the noria (water wheel), the Pump House'),
    dict(exit='Corner Passage', family='Minotaur', wind='south-east', isle='Isle_CornerBar', isle_name='Corner Isle', building='the Corner Hall',
         step=None, bar_name='Minotaur Bar', hall='The Hall of the Minotaurs',
         sights='Corner Isle and the Corner Hall standing in the sea, its dragons and fountain'),
    dict(exit='Bird Stair', family='Albatross', wind='north-west', isle='Isle_Albatross', isle_name='Albatross Isle', building='the Bird Tower',
         step=None, bar_name='Alcove Bar', hall='The Alcove of the Dead',
         sights='the Bird Tower: a stone-jump climb to the marble nest, the albatross and the giant egg'),
]
CHAIN = {c['exit']: c for c in CHAINS}
for _c in CHAINS:
    _c['color'] = FAMILY_COLORS[_c['family']]; _c['ink'] = FAMILY_COLORS_INK[_c['family']]
    _c['road'] = f"{_c['family']} road"
    _c['group'] = f"{_c['family']} road - {_c['exit']} to {_c['hall']}"
    _c['dest'] = ' -> '.join(([_c['step'][1][0].upper() + _c['step'][1][1:]] if _c['step'] else []) +
                             [f"{_c['isle_name']} ({_c['building']})", _c['bar_name'], _c['hall']])
# which sand belongs to which road (every island, shoal and bar has exactly one)
SAND_NAMES = {}
for _c in CHAINS:
    SAND_NAMES[_c['isle']] = (_c['isle_name'], _c['exit'])
    if _c['step']: SAND_NAMES[_c['step'][0]] = (_c['step'][1][0].upper() + _c['step'][1][1:], _c['exit'])
# where each road's isle building stands: entrance (x, z), yaw (local +z runs from the door into the building), footprint
# (width, length); the Bird Tower is given by its centre
_IC = {i[0]: i[1] for i in ISLANDS}
def _yaw_to(dx, dz): return math.degrees(math.atan2(dx, dz)) % 360
_BLD = {'Sea Gate': ((_IC['Isle_West'][0] + 12.0, _IC['Isle_West'][1]), 270.0, (14.0, 22.0), False),
        'East Water Stair': ((_IC['Isle_Ruin'][0] + 14.0, _IC['Isle_Ruin'][1]), 90.0, (22.0, 34.6), False),
        'Tower Door': ((_IC['Isle_SouthBeach'][0] - 30.0, _IC['Isle_SouthBeach'][1] + 8.0), 180.0, (14.0, 22.0), False),
        'Aqueduct Arch': ((_IC['Isle_Pump'][0] + 14.0, _IC['Isle_Pump'][1]), 90.0, (14.0, 22.0), False),
        'Corner Passage': (tuple(CORNER_HALL['entrance']), CORNER_HALL['ry'], (22.0, 34.6), False),
        'Bird Stair': (tuple(_IC['Isle_Albatross']), (_yaw_to(-_IC['Isle_Albatross'][0], -_IC['Isle_Albatross'][1]) + 180.0) % 360, (12.0, 12.0), True)}
for _c in CHAINS: _c['bpos'], _c['bry'], _c['bsize'], _c['bcentred'] = _BLD[_c['exit']]
# what each far wing could become (from the book; see the explainer page) - keyed by the exit whose line it ends
WING_IDEAS = {c['exit']: c['hall'] for c in CHAINS}
# the road statues (one family per road), their base scale (size 1 = human scale) and footprint (width x, length z) at scale 1
FAM_MESH = {'Elephant': 'Statue_Elephant', 'Gorilla': 'Statue_Beast', 'Boy with Cymbals': 'Statue_Child', 'Angel': 'Statue_WingedFigure',
            'Minotaur': 'Statue_Minotaur', 'Albatross': 'Statue_Albatross'}
FAM_BASE = {'Elephant': 0.9, 'Gorilla': 1.0, 'Boy with Cymbals': 2.4, 'Angel': 1.0, 'Minotaur': 1.0, 'Albatross': 1.05}
FAM_EXT = {'Elephant': (1.19, 2.29), 'Gorilla': (1.12, 1.35), 'Boy with Cymbals': (0.4, 0.38), 'Angel': (0.85, 0.85), 'Minotaur': (0.9, 0.7),
           'Albatross': (0.9, 0.8)}      # footprints of the recarved statues (x, z at scale 1; wings may overhang)

def world_map():
    import islands as IS
    WL = {'Wing_1': 193.7, 'Wing_2': 158.6, 'Wing_3': 134.0}
    IS.add_wing_bars(WL)
    frames = IS.wing_frames(WL)
    bar_of = {f['name']: f['exit'] for f in frames}
    isl = []
    for ix, i in enumerate(IS.ISLANDS):
        nm = i[0]
        if nm in SAND_NAMES: label, ex_ = SAND_NAMES[nm]; kind = 'isle' if nm == CHAIN[ex_]['isle'] else 'step'
        elif nm in bar_of: ex_ = bar_of[nm]; label = CHAIN[ex_]['bar_name']; kind = 'bar'
        else: label, ex_, kind = nm, None, 'other'
        isl.append(dict(name=nm, label=label, exit=ex_, kind=kind, c=list(i[1]), r=list(i[2]), rot=(i[6] if len(i) > 6 else 0),
                        tidal=i[3] < 0.3, outline=[[round(x, 1), round(z, 1)] for x, z in IS.outline(ix)]))
    out = dict(G=G, half=HALF, islands=isl, corner_hall=CORNER_HALL, wreck=WRECK, cascade=list(CASCADE[0]), spawn=SPAWN,
               exits={n: dict(cell=e['cell'], side=e['side'], pos=cell_pos(e['cell']), line=[list(v) for v in IS.gate_line(n)])
                      for n, e in EXITS.items()},
               colors=FAMILY_COLORS, ink=FAMILY_COLORS_INK, book=FAMILY_BOOK, why=FAMILY_WHY, quests=QUESTS,
               chains=[{k: (list(v) if isinstance(v, tuple) else v) for k, v in c.items()} for c in CHAINS])
    out['wings'] = [dict(pos=list(f['pos']), ry=f['ry'], mesh=f['mesh'], exit=f['exit'], idea=WING_IDEAS[f['exit']], bar=list(f['bar']),
                         radii=list(f['radii']), endon=f['endon'], hall=list(f['hall']), hall_ry=f['hall_ry'], length=f['length'])
                    for f in frames]
    # the painted mooring poles of each wade, from the last layout run (if there is one)
    lay = os.path.join(HERE, '..', 'out', 'Data', 'HouseLayout.json')
    poles = {c['exit']: [] for c in CHAINS}
    if os.path.exists(lay):
        grp = {c['group']: c['exit'] for c in CHAINS}
        for o in json.load(open(lay))['objects']:
            if o.get('mesh') == 'Briccola' and o.get('group') in grp: poles[grp[o['group']]].append([round(o['p'][0], 1), round(o['p'][2], 1)])
    out['poles'] = poles
    return out

if __name__ == '__main__':
    import sys; sys.path.insert(0, HERE)
    print(json.dumps(world_map(), indent=1)[:1500])
    json.dump(world_map(), open(os.path.join(HERE, '..', 'maze', 'worldmap.json'), 'w'), indent=1)
