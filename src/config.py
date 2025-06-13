# --- LIBRARIES
import time
import openpyxl
import folium
import matplotlib.pyplot as plt
import numpy as np
import openrouteservice
import pandas as pd
from folium.plugins import HeatMap
from geopy.distance import geodesic
from openrouteservice.exceptions import ApiError

# --- CONFIG ---
TRAVEL_TIME_THRESHOLD = 30  # in minutes
DISTANCE_FILTER_MILES = 35  # skip distant locations
POP_COLUMN = "pop_below_18"  # adjust if needed
