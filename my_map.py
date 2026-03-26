from flask import Flask, request
import folium
import requests
import math

app = Flask(__name__)

# Distance calculation
def distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@app.route("/")
def home():
    return """
    <h2>Nearby Medical Services (≤ 1 km)</h2>
    <button onclick="getLocation()">Show Nearby Medical Facilities</button>

    <script>
    function getLocation(){
        navigator.geolocation.getCurrentPosition(function(position){

            let lat = position.coords.latitude;
            let lon = position.coords.longitude;

            window.location.href="/map?lat="+lat+"&lon="+lon;
        });
    }
    </script>
    """


@app.route("/map")
def show_map():

    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    m = folium.Map(location=[lat, lon], zoom_start=15)

    # User marker
    folium.Marker(
        [lat, lon],
        popup="Your Location",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Overpass Query (1 km radius)
    query = f"""
    [out:json];
    (
      node(around:1000,{lat},{lon})["amenity"~"hospital|clinic|doctors|pharmacy"];
      way(around:1000,{lat},{lon})["amenity"~"hospital|clinic|doctors|pharmacy"];
      node(around:1000,{lat},{lon})["shop"="chemist"];
      node(around:1000,{lat},{lon})["shop"="pharmacy"];
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"
    response = requests.get(url, params={'data': query})
    data = response.json()

    for element in data["elements"]:

        tags = element.get("tags", {})
        name = tags.get("name", "Medical Facility")

        if element["type"] == "node":
            lat_p = element["lat"]
            lon_p = element["lon"]
        else:
            lat_p = element["center"]["lat"]
            lon_p = element["center"]["lon"]

        dist = distance(lat, lon, lat_p, lon_p)

        # Show only ≤ 1 km
        if dist <= 1000:

            if tags.get("amenity") == "hospital":
                color = "blue"
            elif tags.get("amenity") == "clinic":
                color = "purple"
            elif tags.get("amenity") == "doctors":
                color = "orange"
            else:
                color = "green"

            folium.Marker(
                [lat_p, lon_p],
                popup=f"{name} ({int(dist)} m)",
                icon=folium.Icon(color=color)
            ).add_to(m)

    return m._repr_html_()


if __name__ == "__main__":
    app.run(debug=True)
