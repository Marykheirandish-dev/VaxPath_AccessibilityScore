# --- LOAD DATA ---
zcta_df = pd.read_csv(
    "/Users/MKHEIRA/Library/CloudStorage/GoogleDrive-marykheirandish69@gmail.com/My Drive/Projects/VAXPath_AccessibilityScore/VaxPath_AccessibilityScore/data/raw/zcta_score_data.csv"
)
zcta_df = zcta_df.iloc[-30:-7].reset_index(drop=True)

provider_df = pd.read_csv(
    "/Users/MKHEIRA/Library/CloudStorage/GoogleDrive-marykheirandish69@gmail.com/My Drive/Projects/VAXPath_AccessibilityScore/VaxPath_AccessibilityScore/data/raw/vfc_providers_geocoded.csv"
)
# Safety check
if POP_COLUMN not in zcta_df.columns:
    raise ValueError(f"Missing population column: '{POP_COLUMN}'")

# --- SETUP CLIENT ---
client = openrouteservice.Client(key=ORS_KEY)


# --- GEODESIC FILTER FUNCTION ---
def filter_nearby_zctas(provider_coord, zcta_coords, max_miles):
    return [
        idx
        for idx, zcta_coord in enumerate(zcta_coords)
        if geodesic(
            (provider_coord[1], provider_coord[0]), (zcta_coord[1], zcta_coord[0])
        ).miles
        <= max_miles
    ]


# --- ORS RETRY WRAPPER ---
def ors_matrix_with_retry(
    client, locations, profile, sources, destinations, max_retries=5, sleep_seconds=5
):
    attempt = 0
    while attempt < max_retries:
        try:
            return client.distance_matrix(
                locations=locations,
                profile=profile,
                sources=sources,
                destinations=destinations,
                metrics=["duration"],
                resolve_locations=False,
            )
        except ApiError as e:
            if "Rate limit exceeded" in str(e):
                wait = (attempt + 1) * sleep_seconds
                print(
                    f"⏳ Rate limit hit. Waiting {wait}s before retrying (attempt {attempt + 1})..."
                )
                time.sleep(wait)
                attempt += 1
            else:
                print(f"❌ ORS API error: {e}")
                break
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
            break
    return None


# --- SETUP COORDINATES ---
zcta_coords = list(zip(zcta_df["lon"], zcta_df["lat"]))
provider_coords = list(zip(provider_df["lon"], provider_df["lat"]))

# --- STEP 1: Compute Rj per Provider ---
provider_ratios = []

for i, provider in provider_df.iterrows():
    print(f"🔄 Processing provider {i + 1}/{len(provider_df)}")
    nearby_zcta_idxs = filter_nearby_zctas(
        provider_coords[i], zcta_coords, max_miles=DISTANCE_FILTER_MILES
    )

    if not nearby_zcta_idxs:
        print(f"⚠️ No nearby ZCTAs — skipping provider {i}")
        provider_ratios.append({"Rj": 0, "coords": provider_coords[i]})
        continue

    matrix = ors_matrix_with_retry(
        client=client,
        locations=[provider_coords[i]] + [zcta_coords[k] for k in nearby_zcta_idxs],
        profile="driving-car",
        sources=[0],
        destinations=list(range(1, len(nearby_zcta_idxs) + 1)),
    )

    if matrix is None or "durations" not in matrix:
        durations = [None] * len(nearby_zcta_idxs)
    else:
        durations = matrix["durations"][0]

    catchment_pop = 0
    for j, duration in zip(nearby_zcta_idxs, durations):
        if duration is None:
            continue
        travel_time = duration / 60
        if travel_time <= TRAVEL_TIME_THRESHOLD:
            catchment_pop += zcta_df.loc[j, POP_COLUMN]

    Rj = 1 / catchment_pop if catchment_pop > 0 else 0
    provider_ratios.append({"Rj": Rj, "coords": provider_coords[i]})

# --- STEP 2: Compute As per ZCTA ---
access_scores = []

for j, zcta in zcta_df.iterrows():
    print(f"🔄 Processing ZCTA {j + 1}/{len(zcta_df)}")

    nearby_provider_idxs = filter_nearby_zctas(
        (zcta["lon"], zcta["lat"]), provider_coords, max_miles=DISTANCE_FILTER_MILES
    )
    if not nearby_provider_idxs:
        access_scores.append(0)
        continue

    matrix = ors_matrix_with_retry(
        client=client,
        locations=[(zcta["lon"], zcta["lat"])]
        + [provider_coords[k] for k in nearby_provider_idxs],
        profile="driving-car",
        sources=[0],
        destinations=list(range(1, len(nearby_provider_idxs) + 1)),
    )

    if matrix is None or "durations" not in matrix:
        durations = [None] * len(nearby_provider_idxs)
    else:
        durations = matrix["durations"][0]

    As = 0
    for idx, duration in zip(nearby_provider_idxs, durations):
        if duration is None:
            continue
        travel_time = duration / 60
        if travel_time <= TRAVEL_TIME_THRESHOLD:
            As += provider_ratios[idx]["Rj"]

    access_scores.append(As)

# --- SAVE OUTPUT ---
zcta_df["Accessibility_Score"] = np.round(access_scores, 6)
zcta_df[["ZCTA", "Accessibility_Score"]].to_csv("2sfca_vfc_ga_1st.csv", index=False)
zcta_df[["ZCTA", "Accessibility_Score"]].to_excel("2sfca_vfc_ga_1st.xlsx", index=False)
print("✅ Saved accessibility scores to Excel and CSV.")

# --- HEATMAP ---
m = folium.Map(location=[33.75, -84.4], zoom_start=9)
heat_data = [
    [row["lat"], row["lon"], row["Accessibility_Score"]]
    for _, row in zcta_df.iterrows()
    if row["Accessibility_Score"] > 0
]
HeatMap(heat_data, radius=15).add_to(m)
m.save("2sfca_vfc_map.html")
print("✅ Saved interactive map to '2sfca_vfc_map.html'")

# --- SCATTER PLOT ---
plt.figure(figsize=(10, 8))
sc = plt.scatter(
    zcta_df["lon"],
    zcta_df["lat"],
    c=zcta_df["Accessibility_Score"],
    cmap="viridis",
    s=100,
    edgecolors="black",
    label="ZCTAs",
)
plt.scatter(
    provider_df["lon"],
    provider_df["lat"],
    color="red",
    marker="^",
    s=150,
    label="VFC Providers",
)
plt.colorbar(sc, label="Accessibility Score (2SFCA)")
plt.title("Spatial Accessibility to VFC Providers in Georgia")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
