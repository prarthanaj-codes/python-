# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template
import random
import copy

app = Flask(__name__)

COLS = 30
ROWS = 22

EMPTY  = 0
PLANT  = 1
RABBIT = 2
FOX    = 3

LEVELS = [
    {"level":1,"name":"The Beginning","description":"Keep rabbits AND foxes alive for 30 ticks!","target_ticks":30,"min_rabbits":1,"min_foxes":1,"plant_chance":0.35,"rabbit_chance":0.12,"fox_chance":0.05},
    {"level":2,"name":"Growing Pains","description":"Survive 60 ticks with 5+ rabbits and 2+ foxes!","target_ticks":60,"min_rabbits":5,"min_foxes":2,"plant_chance":0.30,"rabbit_chance":0.10,"fox_chance":0.04},
    {"level":3,"name":"Wild Balance","description":"Reach 100 ticks keeping all 3 species alive!","target_ticks":100,"min_rabbits":3,"min_foxes":1,"plant_chance":0.25,"rabbit_chance":0.08,"fox_chance":0.03},
    {"level":4,"name":"Harsh Winter","description":"150 ticks! Plants spread slowly - manage carefully.","target_ticks":150,"min_rabbits":5,"min_foxes":2,"plant_chance":0.15,"rabbit_chance":0.06,"fox_chance":0.03},
    {"level":5,"name":"Apex Predator","description":"200 ticks! Scarce resources, extreme challenge.","target_ticks":200,"min_rabbits":8,"min_foxes":3,"plant_chance":0.12,"rabbit_chance":0.05,"fox_chance":0.025},
]

PLANT_SPREAD_CHANCE  = 0.07
RABBIT_BREED_CHANCE  = 0.20
RABBIT_STARVE_CHANCE = 0.10
FOX_BREED_CHANCE     = 0.13
FOX_STARVE_CHANCE    = 0.18

state = {
    "grid": [[EMPTY]*COLS for _ in range(ROWS)],
    "tick": 0,
    "history": {"plant": [], "rabbit": [], "fox": []},
    "score": 0,
    "level": 1,
    "level_complete": False,
    "game_over": False,
    "high_score": 0,
    "interventions_left": 3,
}

def get_neighbors(grid, r, c):
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                neighbors.append((nr, nc, grid[nr][nc]))
    return neighbors

def count_type(neighbors, t):
    return sum(1 for _, _, v in neighbors if v == t)

def simulate_tick(grid):
    new_grid = copy.deepcopy(grid)
    cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
    random.shuffle(cells)
    for r, c in cells:
        cell = grid[r][c]
        neighbors = get_neighbors(grid, r, c)
        if cell == EMPTY:
            plant_neighbors = count_type(neighbors, PLANT)
            if plant_neighbors > 0 and random.random() < PLANT_SPREAD_CHANCE * plant_neighbors:
                new_grid[r][c] = PLANT
        elif cell == RABBIT:
            plant_cells = [(nr, nc) for nr, nc, v in neighbors if v == PLANT]
            empty_cells = [(nr, nc) for nr, nc, v in neighbors if v == EMPTY]
            if plant_cells:
                pr, pc = random.choice(plant_cells)
                new_grid[pr][pc] = EMPTY
                if empty_cells and random.random() < RABBIT_BREED_CHANCE:
                    br, bc = random.choice(empty_cells)
                    new_grid[br][bc] = RABBIT
            else:
                if random.random() < RABBIT_STARVE_CHANCE:
                    new_grid[r][c] = EMPTY
        elif cell == FOX:
            rabbit_cells = [(nr, nc) for nr, nc, v in neighbors if v == RABBIT]
            empty_cells  = [(nr, nc) for nr, nc, v in neighbors if v == EMPTY]
            if rabbit_cells:
                rr, rc = random.choice(rabbit_cells)
                new_grid[rr][rc] = EMPTY
                if empty_cells and random.random() < FOX_BREED_CHANCE:
                    br, bc = random.choice(empty_cells)
                    new_grid[br][bc] = FOX
            else:
                if random.random() < FOX_STARVE_CHANCE:
                    new_grid[r][c] = EMPTY
    return new_grid

def count_population(grid):
    plants = rabbits = foxes = 0
    for row in grid:
        for cell in row:
            if cell == PLANT:    plants  += 1
            elif cell == RABBIT: rabbits += 1
            elif cell == FOX:    foxes   += 1
    return plants, rabbits, foxes

def calculate_score(tick, plants, rabbits, foxes, level):
    base = tick * level * 10
    biodiversity = (plants // 10) + (rabbits * 3) + (foxes * 5)
    return base + biodiversity

def get_level_data():
    lvl = state["level"]
    return LEVELS[min(lvl, len(LEVELS)) - 1]

def check_level_status(plants, rabbits, foxes):
    lvl = get_level_data()
    if rabbits == 0 or foxes == 0 or plants == 0:
        return "game_over"
    if state["tick"] >= lvl["target_ticks"] and rabbits >= lvl["min_rabbits"] and foxes >= lvl["min_foxes"]:
        return "level_complete"
    return "running"

def seed_level(level_num):
    lvl = LEVELS[min(level_num, len(LEVELS)) - 1]
    grid = [[EMPTY]*COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            rnd = random.random()
            if rnd < lvl["plant_chance"]:
                grid[r][c] = PLANT
            elif rnd < lvl["plant_chance"] + lvl["rabbit_chance"]:
                grid[r][c] = RABBIT
            elif rnd < lvl["plant_chance"] + lvl["rabbit_chance"] + lvl["fox_chance"]:
                grid[r][c] = FOX
    return grid

def full_state(plants, rabbits, foxes):
    return {
        "grid": state["grid"],
        "tick": state["tick"],
        "counts": {"plant": plants, "rabbit": rabbits, "fox": foxes},
        "history": state["history"],
        "score": state["score"],
        "level": state["level"],
        "level_info": get_level_data(),
        "level_complete": state["level_complete"],
        "game_over": state["game_over"],
        "high_score": state["high_score"],
        "interventions_left": state["interventions_left"],
        "cols": COLS,
        "rows": ROWS
    }

@app.route("/")
def index():
    return render_template("index.html", cols=COLS, rows=ROWS)

@app.route("/api/state")
def get_state():
    p, r, f = count_population(state["grid"])
    return jsonify(full_state(p, r, f))

@app.route("/api/tick", methods=["POST"])
def do_tick():
    if state["game_over"] or state["level_complete"]:
        p, r, f = count_population(state["grid"])
        return jsonify(full_state(p, r, f))
    state["grid"] = simulate_tick(state["grid"])
    state["tick"] += 1
    p, r, f = count_population(state["grid"])
    for key, val in [("plant", p), ("rabbit", r), ("fox", f)]:
        state["history"][key].append(val)
        if len(state["history"][key]) > 60:
            state["history"][key].pop(0)
    state["score"] = calculate_score(state["tick"], p, r, f, state["level"])
    if state["score"] > state["high_score"]:
        state["high_score"] = state["score"]
    status = check_level_status(p, r, f)
    if status == "game_over":
        state["game_over"] = True
    elif status == "level_complete":
        state["level_complete"] = True
    return jsonify(full_state(p, r, f))

@app.route("/api/place", methods=["POST"])
def place_cell():
    data = request.json
    r, c, t = data["row"], data["col"], data["type"]
    if state["tick"] > 0 and not state["game_over"] and not state["level_complete"]:
        if t in [RABBIT, FOX]:
            if state["interventions_left"] <= 0:
                p, rb, f = count_population(state["grid"])
                return jsonify({"error": "No interventions left!", "grid": state["grid"],
                                "counts": {"plant": p, "rabbit": rb, "fox": f},
                                "interventions_left": 0})
            state["interventions_left"] -= 1
    if 0 <= r < ROWS and 0 <= c < COLS:
        state["grid"][r][c] = t
    p, rb, f = count_population(state["grid"])
    return jsonify({"grid": state["grid"], "counts": {"plant": p, "rabbit": rb, "fox": f},
                    "interventions_left": state["interventions_left"]})

@app.route("/api/next_level", methods=["POST"])
def next_level():
    state["level"] = min(state["level"] + 1, len(LEVELS))
    state["grid"] = seed_level(state["level"])
    state["tick"] = 0
    state["history"] = {"plant": [], "rabbit": [], "fox": []}
    state["level_complete"] = False
    state["game_over"] = False
    state["interventions_left"] = 3
    p, r, f = count_population(state["grid"])
    return jsonify(full_state(p, r, f))

@app.route("/api/start_level", methods=["POST"])
def start_level():
    data = request.json
    lvl = data.get("level", 1)
    state["level"] = lvl
    state["grid"] = seed_level(lvl)
    state["tick"] = 0
    state["history"] = {"plant": [], "rabbit": [], "fox": []}
    state["score"] = 0
    state["level_complete"] = False
    state["game_over"] = False
    state["interventions_left"] = 3
    p, r, f = count_population(state["grid"])
    return jsonify(full_state(p, r, f))

@app.route("/api/reset", methods=["POST"])
def reset():
    state["grid"] = [[EMPTY]*COLS for _ in range(ROWS)]
    state["tick"] = 0
    state["history"] = {"plant": [], "rabbit": [], "fox": []}
    state["score"] = 0
    state["level"] = 1
    state["level_complete"] = False
    state["game_over"] = False
    state["interventions_left"] = 3
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
