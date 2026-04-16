 Microplastics Simulation & Visualization

This project simulates the spread of microplastics in water bodies and visualizes the results on an interactive map using Folium
.
It combines simulation logic (Python) with geospatial visualization to better understand pollution flow and accumulation.

 Project Structure
NANO/
 ├── app.py                        # Flask app to serve the map
 ├── depth_modified.py             # Simulation code (depth-based model)
 ├── integration_app.py            # Data integration / processing script
 ├── geocoded_500_successful.csv   # Dataset with geocoded points
 ├── Microplastics_Clean_Essential.csv  # Core dataset
 ├── requirements.txt              # Python dependencies
 ├── Procfile                      # Deployment config (for Render)
 ├── templates/
 │    └── microplastics_map.html   # Folium map (generated visualization)
 └── simulation_out.log            # Simulation logs

 How to Run Locally

Clone the repo

git clone https://github.com/your-username/your-repo.git
cd your-repo


Create virtual environment (recommended)

python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate


Install dependencies

pip install -r requirements.txt


Run Flask app

python app.py


Open in browser
Navigate to http://127.0.0.1:5000/ to view the interactive map.

Deployment (Render)

Push this repo to GitHub.

Go to Render
 → New Web Service.

Connect your GitHub repo.

Configure:

Build command:

pip install -r requirements.txt


Start command:

gunicorn app:app


Choose Free Plan and deploy.

Your app will be live at:

https://your-app-name.onrender.com

 Features

Simulates microplastic flow and accumulation.

Uses Folium maps for interactive visualization.

Works with real datasets (.csv).

Can be deployed to the web for public access.

 Future Improvements

Add real-time simulation updates instead of static maps.

Integrate with machine learning models to predict plastic movement.

Expand dataset coverage for more accuracy.
