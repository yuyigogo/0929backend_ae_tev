import json
import os
import re
import sys
import uuid

from paho.mqtt import client as mqtt_client
# this is a global variable to store parsed data
from paho.mqtt.client import base62

uhf_loading_data, ae_tev_loading_data = {}, {}


def connect_mqtt(mqtt_config: dict) -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"my own client_id: {client._client_id} Connected to MQTT Broker!")
        else:
            print(
                f"client_id: {client._client_id} Failed to connect, return code %d\n",
                rc,
            )

    client_config = mqtt_config["client_config"]
    my_client_id = base62(uuid.uuid4().int, padding=22)
    client = mqtt_client.Client(my_client_id)
    client.username_pw_set(username=client_config["user"], password=client_config["pw"])
    client.on_connect = on_connect
    client.connect(
        client_config["host"], client_config["port"],
    )
    return client


def subscribe(client: mqtt_client, mqtt_config: dict):
    def on_message(client, userdata, msg):
        try:
            loading_collected_data(msg, mqtt_config)
        except Exception as e:
            print(
                f"loading data error on topic: {msg.topic}--data: {msg.payload.decode()}"
            )

    sensor_id_name_dict = mqtt_config["sensor_id_name_dict"]
    subscribe_client_id = mqtt_config["client_config"]["subscribe_client_id"]
    subscribed_topics = [
        (f"/{subscribe_client_id}/subnode/{sensor_id}/data_ctrl/property", 0)
        for sensor_id in sensor_id_name_dict.keys()
    ]
    client.subscribe(subscribed_topics)
    client.on_message = on_message


def loading_collected_data(msg, mqtt_config):
    global uhf_loading_data, ae_tev_loading_data
    topic = msg.topic
    data = json.loads(msg.payload.decode())
    UHF = data.get("params", {}).get("UHF")
    AE = data.get("params", {}).get("AE")
    ret = re.match(
        r"/(?P<client_id>[a-zA-Z0-9]+)/subnode/(?P<sensor_id>[a-zA-Z0-9]+)/data_ctrl/property",
        topic,
    )
    if not ret or (not UHF and not AE):
        # for now only load uhf data
        return uhf_loading_data, ae_tev_loading_data
    client_id = ret.group(1)
    sensor_id = ret.group(2)
    sensor_id_name_dict = mqtt_config["sensor_id_name_dict"]
    sensor_type = sensor_id_name_dict.get(sensor_id)
    if not sensor_type:
        return uhf_loading_data, ae_tev_loading_data

    print(
        f"client_id: {client_id}------sensor_id: {sensor_id}-----sensor_type: {sensor_type}"
    )
    base_path = os.path.dirname(sys.argv[0])
    if not base_path:
        base_path = "."
    parsed_data = assemble_loading_data(sensor_id, data, sensor_id_name_dict)
    if sensor_type[0] == "0000000000000002":
        ae_tev_loading_data.update(parsed_data)
        with open(f"{base_path}/ae_tev_loading_data.json", "w") as f:
            f.write(json.dumps(ae_tev_loading_data))
    elif sensor_type[0] == "0000000000000003":
        uhf_loading_data.update(parsed_data)
        with open(f"{base_path}/uhf_loading_data.json", "w") as f:
            f.write(json.dumps(uhf_loading_data))
    return uhf_loading_data, ae_tev_loading_data


def assemble_loading_data(sensor_id: str, origin_data: dict, sensor_id_name_dict: dict):
    sensor_type = sensor_id_name_dict.get(sensor_id)
    t = ""
    data_type = None
    if sensor_type[0] == "0000000000000002":
        # loading AE/TEV data
        data_type = "AE/TEV"
        t = origin_data["params"]["AE"].get("acqtime")
    elif sensor_type[0] == "0000000000000003":
        # loading UHF data
        data_type = "UHF"
        t = origin_data["params"]["UHF"].get("acqtime")
    return {
        sensor_id: {
            "test_location_name": sensor_id_name_dict[sensor_id][1],
            "data_type": data_type,
            "acquisition_time": parse_acquisition_time(t),
            "params": origin_data.get("params"),
        }
    }


def parse_acquisition_time(t: str) -> str:
    return f"{t[:4]}-{t[4:6]}-{t[6:8]} {t[8:10]}:{t[10:12]}:{t[12:]}"


def loading_mqtt_config() -> dict:
    base_path = os.path.dirname(sys.argv[0])
    if not base_path:
        base_path = "."
    with open(f"{base_path}/mqtt_config.json", "r", encoding="utf-8") as f:
        mqtt_config = f.read()
    return json.loads(mqtt_config)


def run():
    mqtt_config = loading_mqtt_config()
    client = connect_mqtt(mqtt_config)
    subscribe(client, mqtt_config)
    client.loop_forever()


if __name__ == "__main__":
    run()
