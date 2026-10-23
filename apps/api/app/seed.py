"""Seed base determinístico: 142 pontos, linhas e garagens. A calibração do cenário Demo está em demo.py."""
import random

N_STOPS = 142
STREETS = [
    "Av. Paulista", "R. da Consolação", "Av. Rebouças", "Av. Brigadeiro Faria Lima", "Av. Ipiranga",
    "R. Augusta", "Av. São João", "Av. Brasil", "Av. Santo Amaro", "R. Vergueiro", "Av. Angélica",
    "Av. Nove de Julho", "Av. Sumaré", "R. Teodoro Sampaio", "Av. Pompeia", "R. Oscar Freire",
    "Av. Liberdade", "R. Domingos de Morais", "Av. Jabaquara", "Av. Ibirapuera", "R. Haddock Lobo",
    "Av. Cidade Jardim", "Av. Brás Leme", "Av. Cruzeiro do Sul", "R. Vergueiro Sul",
]
GARAGES = [("GAR-VM", "Garagem Vila Mariana"), ("GAR-SA", "Garagem Santo Amaro"),
           ("GAR-PI", "Garagem Pinheiros"), ("GAR-LP", "Garagem Lapa")]
FIXED_LINES = ["875A", "177H", "6450", "7272"]
# pontos do render 01 (verbatim): ids fixos para o cenário Demo
FIXED_STOPS = {
    "SP-0412": ("Av. Paulista, 1578", ["875A"]),
    "SP-0071": ("Terminal Sto. Amaro · Pl. 3", ["6450"]),
    "SP-0233": ("R. da Consolação, 900", ["177H"]),
    "SP-0587": ("Av. Rebouças, 1200", ["7272"]),
}


def build(seed: int = 42) -> dict:
    rng = random.Random(seed)
    lines = list(FIXED_LINES)
    while len(lines) < 40:
        code = f"{rng.randint(100, 9999)}{rng.choice('ABCDEFGHJKLMNP-')}".rstrip("-")
        if code not in lines:
            lines.append(code)
    line_rows = [(code, rng.randint(6, 15)) for code in lines]

    ids = set(FIXED_STOPS)
    while len(ids) < N_STOPS:
        ids.add(f"SP-{rng.randint(1, 999):04d}")
    stops, stop_lines = [], []
    for sid in sorted(ids):
        if sid in FIXED_STOPS:
            name, ls = FIXED_STOPS[sid]
        else:
            name = f"{rng.choice(STREETS)}, {rng.randint(10, 2400)}"
            ls = rng.sample(lines, rng.randint(1, 3))
        arrival = round(rng.uniform(0.8, 2.6), 2)
        stops.append((sid, name, arrival, round(arrival * 1.2, 2)))
        stop_lines += [(sid, l) for l in ls]
    initial = {s[0]: rng.randint(4, 12) for s in stops}
    return {"lines": line_rows, "garages": GARAGES, "stops": stops, "stop_lines": stop_lines, "initial": initial}


async def run(conn) -> bool:
    cur = await conn.execute("SELECT count(*) AS n FROM stops")
    if (await cur.fetchone())["n"] > 0:
        return False
    d = build()
    async with conn.cursor() as cur:
        await cur.executemany("INSERT INTO lines(id, headway_min) VALUES (%s, %s)", d["lines"])
        await cur.executemany("INSERT INTO garages(id, name) VALUES (%s, %s)", d["garages"])
        await cur.executemany("INSERT INTO stops(id, name, arrival_rate, board_rate) VALUES (%s, %s, %s, %s)", d["stops"])
        await cur.executemany("INSERT INTO stop_lines(stop_id, line_id) VALUES (%s, %s)", d["stop_lines"])
        await cur.executemany("INSERT INTO stop_state(stop_id, count) VALUES (%s, %s)", list(d["initial"].items()))
    return True
