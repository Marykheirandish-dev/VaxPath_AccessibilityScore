# --- LIBRARIES
import time

import folium
import matplotlib.pyplot as plt
import numpy as np
import openrouteservice
import pandas as pd
from folium.plugins import HeatMap
from geopy.distance import geodesic
from openrouteservice.exceptions import ApiError

# --- CONFIG ---
ORS_KEY = "5b3ce3597851110001cf62489b5896d9ce48408784b8cd929b44c9b0"
TRAVEL_TIME_THRESHOLD = 30  # in minutes
DISTANCE_FILTER_MILES = 35  # skip distant locations
POP_COLUMN = "population"  # adjust if needed
