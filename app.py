from flask import Flask, jsonify
from influxdb_client import InfluxDBClient, QueryApi
import os
import logging

# Initialize Flask app
app = Flask(__name__)

# Set up logging configuration based on the environment variable
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

if LOG_LEVEL == 'DEBUG':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# Create a logger
logger = logging.getLogger(__name__)

# InfluxDB configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', '')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'dhts')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'airlytic')
INFLUXDB_RANGE = os.getenv('INFLUXDB_RANGE', '0')

# Create InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

@app.route('/latest', methods=['GET'])
def get_aqi_data():
    logger.debug(f"Querying InfluxDB with range: {INFLUXDB_RANGE}")

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
    |> range(start: {INFLUXDB_RANGE})
    |> filter(fn: (r) => r._measurement == "data")
    |> filter(fn: (r) => r._field == "Latitude" or r._field == "Longitude" or r._field == "AQI")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> limit(n: 100)
    '''
    
    try:
        result = query_api.query(org=INFLUXDB_ORG, query=query)
    except Exception as e:
        logger.error(f"Error querying InfluxDB: {e}")
        return jsonify({"error": "Failed to query data"}), 500
    
    # Process the result to extract required fields
    data_list = []
    for table in result:
        for record in table.records:
            data = {
                "latitude": record.values.get("Latitude"),
                "longitude": record.values.get("Longitude"),
                "AQI": record.values.get("AQI")
            }
            data_list.append(data)

    logger.info(f"Successfully retrieved {len(data_list)} records.")
    return jsonify(data_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
