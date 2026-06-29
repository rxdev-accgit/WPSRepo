from flask import Flask, jsonify
import random
import time
import threading

app = Flask(__name__)

# ──────────────────────────────────────────
# CONFIGURATION — edit these to your liking
# ──────────────────────────────────────────
RESET_INTERVAL = 5 * 60   # 5 minutes in seconds
MAX_ITEMS      = 3         # how many items appear in the shop per rotation

# Item table — mirrors your Lua Items ModuleScript
# Format: "Item Name": { "weight": int, "stock": int, "price": int }
ITEMS = {
    "Item 1": { "weight": 30, "stock": 20, "price": 100 },
    "Item 2": { "weight": 20, "stock": 10, "price": 200 },
    "Item 3": { "weight": 10, "stock": 5,  "price": 300 },
    "Super Rare Item 4": { "weight": 3,  "stock": 1,  "price": 400 },
}

# ──────────────────────────────────────────
# SHOP STATE
# ──────────────────────────────────────────
shop_lock        = threading.Lock()
current_shop     = {}   # { "Item Name": { "stock": int, "price": int } }
last_reset_time  = 0
shop_id          = 0


def generate_shop():
    """Weighted probability selection — same logic as your ProbabilityCalculator."""
    global current_shop, last_reset_time, shop_id

    # Build weighted pool
    pool = []
    for name, data in ITEMS.items():
        for _ in range(data["weight"]):
            pool.append(name)

    # Pick unique items
    random.shuffle(pool)
    chosen = {}
    seen   = set()

    for pick in pool:
        if len(chosen) >= MAX_ITEMS:
            break
        if pick not in seen:
            seen.add(pick)
            chosen[pick] = {
                "stock": ITEMS[pick]["stock"],
                "price": ITEMS[pick]["price"],
            }

    with shop_lock:
        current_shop    = chosen
        last_reset_time = int(time.time())
        shop_id        += 1

    print(f"[SHOP]: Generated new shop (ID {shop_id}) — {list(chosen.keys())}")


def reset_loop():
    """Background thread that resets the shop every RESET_INTERVAL seconds."""
    while True:
        time.sleep(RESET_INTERVAL)
        generate_shop()


# ──────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────

@app.route("/shop", methods=["GET"])
def get_shop():
    """
    Returns the current shop state.
    Roblox calls this via HttpService:GetAsync().

    Response:
    {
        "shop_id": int,
        "last_reset": int (Unix timestamp),
        "next_reset": int (Unix timestamp),
        "items": {
            "Item Name": { "stock": int, "price": int },
            ...
        }
    }
    """
    with shop_lock:
        return jsonify({
            "shop_id":    shop_id,
            "last_reset": last_reset_time,
            "next_reset": last_reset_time + RESET_INTERVAL,
            "items":      current_shop,
        })


@app.route("/purchase/<item_name>", methods=["POST"])
def purchase(item_name):
    """
    Deducts 1 from an item's stock on purchase.
    Roblox calls this via HttpService:PostAsync().

    Response:
        { "success": true }
        { "success": false, "reason": "Out of stock" }
        { "success": false, "reason": "Item not in shop" }
    """
    with shop_lock:
        if item_name not in current_shop:
            return jsonify({ "success": False, "reason": "Item not in shop" }), 404

        if current_shop[item_name]["stock"] <= 0:
            return jsonify({ "success": False, "reason": "Out of stock" }), 400

        current_shop[item_name]["stock"] -= 1
        print(f"[SHOP]: Purchase — {item_name} | Stock remaining: {current_shop[item_name]['stock']}")
        return jsonify({ "success": True })


@app.route("/reset", methods=["POST"])
def manual_reset():
    """
    Manually triggers a shop reset.
    Useful for admin commands or testing.
    """
    generate_shop()
    return jsonify({ "success": True, "shop_id": shop_id })


# ──────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────
if __name__ == "__main__":
    generate_shop()
    thread = threading.Thread(target=reset_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000)
