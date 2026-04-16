from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # Serve the existing Folium map
    return render_template("microplastics_map.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
