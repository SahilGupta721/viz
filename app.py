import os
import requests
import matplotlib.pyplot as plt
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS  # CORS import
from io import BytesIO
from dotenv import load_dotenv  

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://vizweather.vercel.app"}}) 

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = os.getenv("BASE_URL")
FORECAST_URL = os.getenv("FORECAST_URL")

if not API_KEY or not BASE_URL or not FORECAST_URL:
    raise ValueError("Missing required environment variables. Check your .env file.")

@app.after_request
def apply_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route("/weather", methods=["GET"])
def get_weather():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    params = {"q": city, "appid": API_KEY, "units": "metric"}
    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        data = response.json()

        weather_data = {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "winds": f"{round(data['wind']['speed'] * 2.237, 1)} mph",
            "sky_condition": data["weather"][0]["description"].title(),
            "rain": f"Rain volume in last hour: {data.get('rain', {}).get('1h', 0)} mm" if "rain" in data else "No rain",
        }

        return jsonify(weather_data)

    return jsonify({"error": "City not found."}), response.status_code

@app.route("/hourly", methods=["GET"])
def get_hourly():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    params = {"q": city, "appid": API_KEY, "units": "metric"}
    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        data = response.json()
        lat, lon = data["coord"]["lat"], data["coord"]["lon"]

        forecast_params = {"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
        forecast_response = requests.get(FORECAST_URL, params=forecast_params)

        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()

            # Extract hours and temperatures
            hours = [entry["dt_txt"].split(" ")[1][:5] for entry in forecast_data["list"][:8]]
            temperatures = [entry["main"]["temp"] for entry in forecast_data["list"][:8]]

            # Create a transparent graph with white text
            plt.figure(figsize=(10, 6), facecolor='none')  
            plt.plot(hours, temperatures, marker="o", color="white", label="Temperature (°C)")

            plt.title(f"Hourly Temperature Forecast for {city}", color="white")
            plt.xlabel("Time (HH:MM)", color="white")
            plt.ylabel("Temperature (°C)", color="white")

            plt.xticks(rotation=45, color="white")
            plt.yticks(color="white")
            plt.grid(True, linestyle="--", color="gray")
            plt.legend(facecolor='none', edgecolor='white')

            plt.gca().set_facecolor("none")  # Transparent plot background

            img = BytesIO()
            plt.savefig(img, format='png', transparent=True, bbox_inches='tight')  
            img.seek(0)

            return send_file(img, mimetype='image/png', as_attachment=False, download_name='forecast.png')

        return jsonify({"error": "Error fetching hourly forecast data."}), forecast_response.status_code

    return jsonify({"error": "City not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
