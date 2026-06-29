from flask import Flask, jsonify
import random
import time
import threading

app = Flask(__name__)

RESET_INTERVAL = 5 * 60
MAX_ITEMS      = 3

ITEMS = {
    "Sword": { "weight": 30, "stock": 20, "price": 100 }, #example item name
    "Apple": { "weight": 20, "stock": 10, "price": 200 }, #example item name
    "Potion": { "weight": 10, "stock": 5,  "price": 300 }, #example item name
    "Super crystal": { "weight": 3,  "stock": 1,  "price": 400 }, #example item name
}

shop_lock       = threading.Lock()
current_shop    = {}
last_reset_time = 0
shop_id         = 0


def generate_shop():
    global current_shop, last_reset_time, shop_id

    pool = []
    for name, data in ITEMS.items():
        for _ in range(data["weight"]):
            pool.append(name)

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
    while True:
        time.sleep(RESET_INTERVAL)
        generate_shop()


@app.route("/shop", methods=["GET"])
def get_shop():
    with shop_lock:
        return jsonify({
            "shop_id":    shop_id,
            "last_reset": last_reset_time,
            "next_reset": last_reset_time + RESET_INTERVAL,
            "items":      current_shop,
        })


@app.route("/purchase/<item_name>", methods=["POST"])
def purchase(item_name):
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
    generate_shop()
    return jsonify({ "success": True, "shop_id": shop_id })


if __name__ == "__main__":
    generate_shop()
    thread = threading.Thread(target=reset_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000)
