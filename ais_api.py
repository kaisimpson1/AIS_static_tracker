import asyncio
import websockets
import json
import time
import config

latest_by_mmsi = {}
SNAPSHOT_FILE = "vessels.json"

try:
    import config
except ImportError:
    raise RuntimeError(
        "Create config.py from config_example.py and add your API key"
    )


async def connect_ais_stream():
    last_snapshot = 0
    SNAPSHOT_EVERY = 10
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
        print("Connected to AIS stream")
        subscribe_message = {
            "APIKey": config.APIKEY,
            "BoundingBoxes": [[[49.5, -11], [61, 2]]],
            "FilterMessageTypes": ["PositionReport"]
        }

        subscribe_message = json.dumps(subscribe_message)
        await websocket.send(subscribe_message)
        print("Subscription message sent")
        async for message_json in websocket:
            message = json.loads(message_json)
            message_type = message["MessageType"]

            if message_type == "PositionReport":
                ais_message = message['Message']["PositionReport"]
                mmsi = str(ais_message["UserID"])
                lat = ais_message["Latitude"]
                lon = ais_message["Longitude"]

                latest_by_mmsi[mmsi] = {
                    "lat": lat,
                    "lon": lon,
                    "last_seen": time.time()
                }

                now = time.time()
                for mmsi in list(latest_by_mmsi.keys()):
                    if now - latest_by_mmsi[mmsi]["last_seen"] > 15 * 60:
                        del latest_by_mmsi[mmsi]

                ## group snapshot
               
                if now - last_snapshot >= SNAPSHOT_EVERY:
                    last_snapshot = now    
                    print("\n===== SNAPSHOT =====")
                    print("Ships currently tracked:", len(latest_by_mmsi))
                    snapshot = [
                        {
                            "mmsi": mmsi,
                            "lat": v["lat"],
                            "lon": v["lon"],
                            "last_seen": v["last_seen"]
                        }
                        for mmsi, v in latest_by_mmsi.items()
                    ]       
                    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
                        json.dump(snapshot, f)
                    
                    for i, (mmsi, v) in enumerate(latest_by_mmsi.items()):
                        if i >= 10:
                            break
                        age = now - v["last_seen"]
                        print(f"{mmsi}: lat={v['lat']:.5f}, lon={v['lon']:.5f}, age={age:.0f}s")

if __name__ == "__main__":
    asyncio.run(connect_ais_stream())