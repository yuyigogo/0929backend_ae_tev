import json
import os
import sys
from flask import render_template, jsonify, Flask

app = Flask(__name__)


@app.route("/rest/v1/sensor_list/")
def sensor_list():
    base_path = os.path.dirname(sys.argv[0])
    if not base_path:
        base_path = "."
    with open(f"{base_path}/uhf_loading_data.json", "r") as f:
        content = f.read()
        uhf_data = json.loads(content)
    with open(f"{base_path}/ae_tev_loading_data.json", "r") as f:
        content = f.read()
        ae_tev_data = json.loads(content)
    res_data = list(uhf_data.values()) + list(ae_tev_data.values())
    return jsonify(res_data)


@app.route("/sensor_details/")
def sensor_details():
    return render_template("sensor_details.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
