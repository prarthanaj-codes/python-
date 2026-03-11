# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template
import random
import copy

app = Flask(__name__)

# Grid dimensions
COLS = 30
ROWS = 22

# Cell types
EMPTY  = 0
PLANT  = 1
RABBIT = 2
FOX    = 3

# Simulation parameters
PLANT_SPREAD_CHANCE  = 0.07
RABBIT_BREED_CHANCE  = 0.20
RABBIT_STARVE_CHANCE = 0.10
FOX_BREED_CHANCE     = 0.13
FOX_STARVE_CHANCE    = 0.18

# Game state
state = {
    "grid": [[EMPTY]*COLS for _ in range(ROWS)],
    "tick": 0,
    "history": {"plant": [], "rabbit": [], "fox": []}
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

    # Shuffle order to avoid directional bias
    cells = [(r, c) for r in range(ROWS) for c in range(COLS)]
    random.shuffle(cells)

    for r, c in cells:
        cell = grid[r][c]
        neighbors = get_neighbors(grid, r, c)
        neighbor_types = [v for _, _, v in neighbors]
        neighbor_coords = [(nr, nc) for nr, nc, _ in neighbors]

        if cell == EMPTY:
            # Plants spread into empty cells
            plant_neighbors = count_type(neighbors, PLANT)
            if plant_neighbors > 0 and random.random() < PLANT_SPREAD_CHANCE * plant_neighbors:
                new_grid[r][c] = PLANT

        elif cell == PLANT:
            # Plants can be eaten by adjacent rabbits (handled from rabbit side)
            pass

        elif cell == RABBIT:
            # Find adjacent plants to eat
            plant_cells = [(nr, nc) for nr, nc, v in neighbors if v == PLANT]
            empty_cells = [(nr, nc) for nr, nc, v in neighbors if v == EMPTY]

            if plant_cells:
                # Eat a plant
                pr, pc = random.choice(plant_cells)
                new_grid[pr][pc] = EMPTY
                # Try to breed into empty cell
                if empty_cells and random.random() < RABBIT_BREED_CHANCE:
                    br, bc = random.choice(empty_cells)
                    new_grid[br][bc] = RABBIT
            else:
                # No food - might starve
                if random.random() < RABBIT_STARVE_CHANCE:
                    new_grid[r][c] = EMPTY

        elif cell == FOX:
            # Find adjacent rabbits to eat
            rabbit_cells = [(nr, nc) for nr, nc, v in neighbors if v == RABBIT]
            empty_cells  = [(nr, nc) for nr, nc, v in neighbors if v == EMPTY]

            if rabbit_cells:
                # Eat a rabbit
                rr, rc = random.choice(rabbit_cells)
                new_grid[rr][rc] = EMPTY
                # Try to breed
                if empty_cells and random.random() < FOX_BREED_CHANCE:
                    br, bc = random.choice(empty_cells)
                    new_grid[br][bc] = FOX
            else:
                # No food - might starve
                if random.random() < FOX_STARVE_CHANCE:
                    new_grid[r][c] = EMPTY

    return new_grid

def count_population(grid):
    plants = rabbits = foxes = 0
    for row in grid:
        for cell in row:
            if cell == PLANT:  plants  += 1
            elif cell == RABBIT: rabbits += 1
            elif cell == FOX:    foxes   += 1
    return plants, rabbits, foxes

@app.route("/")
def index():
    return render_template("index.html", cols=COLS, rows=ROWS)

@app.route("/api/state")
def get_state():
    plants, rabbits, foxes = count_population(state["grid"])
    return jsonify({
        "grid": state["grid"],
        "tick": state["tick"],
        "counts": {"plant": plants, "rabbit": rabbits, "fox": foxes},
        "history": state["history"],
        "cols": COLS,
        "rows": ROWS
    })

@app.route("/api/tick", methods=["POST"])
def do_tick():
    state["grid"] = simulate_tick(state["grid"])
    state["tick"] += 1
    plants, rabbits, foxes = count_population(state["grid"])

    # Record history (keep last 60 ticks)
    for key, val in [("plant", plants), ("rabbit", rabbits), ("fox", foxes)]:
        state["history"][key].append(val)
        if len(state["history"][key]) > 60:
            state["history"][key].pop(0)

    return jsonify({
        "grid": state["grid"],
        "tick": state["tick"],
        "counts": {"plant": plants, "rabbit": rabbits, "fox": foxes},
        "history": state["history"]
    })

@app.route("/api/place", methods=["POST"])
def place_cell():
    data = request.json
    r, c, t = data["row"], data["col"], data["type"]
    if 0 <= r < ROWS and 0 <= c < COLS:
        state["grid"][r][c] = t
    plants, rabbits, foxes = count_population(state["grid"])
    return jsonify({
        "grid": state["grid"],
        "counts": {"plant": plants, "rabbit": rabbits, "fox": foxes}
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    state["grid"] = [[EMPTY]*COLS for _ in range(ROWS)]
    state["tick"] = 0
    state["history"] = {"plant": [], "rabbit": [], "fox": []}
    return jsonify({"status": "ok"})

@app.route("/api/random", methods=["POST"])
def random_seed():
    state["grid"] = [[EMPTY]*COLS for _ in range(ROWS)]
    state["tick"] = 0
    state["history"] = {"plant": [], "rabbit": [], "fox": []}
    total = ROWS * COLS
    for r in range(ROWS):
        for c in range(COLS):
            rnd = random.random()
            if rnd < 0.30:
                state["grid"][r][c] = PLANT
            elif rnd < 0.42:
                state["grid"][r][c] = RABBIT
            elif rnd < 0.47:
                state["grid"][r][c] = FOX
    plants, rabbits, foxes = count_population(state["grid"])
    return jsonify({
        "grid": state["grid"],
        "tick": state["tick"],
        "counts": {"plant": plants, "rabbit": rabbits, "fox": foxes},
        "history": state["history"]
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
