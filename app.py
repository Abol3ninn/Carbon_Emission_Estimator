import streamlit as st
import spacy
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt

# Ensure the language model is installed
@st.cache_resource
def load_spacy_model():
    model = "en_core_web_sm"
    if importlib.util.find_spec(model) is None:
        subprocess.run(["python", "-m", "spacy", "download", model])
    return spacy.load(model)

nlp = load_spacy_model()

# Geocoding
geolocator = Nominatim(user_agent="carbon_estimator", timeout=5)

# Emission factors in kg CO2 per km
emission_factors = {
    "flight": 0.25,
    "car": 0.12,
    "truck": 0.13,
    "train": 0.05
}

# Alternative suggestions
better_options = {
    "flight": ["train", "car"],
    "car": ["train", "bike"],
    "truck": ["train"],
    "train": ["bike"]
}

# Detect transport method
def detect_transport(text):
    text = text.lower()
    if "flight" in text or "plane" in text:
        return "flight"
    elif "car" in text:
        return "car"
    elif "truck" in text:
        return "truck"
    elif "train" in text:
        return "train"
    else:
        return None

# Extract city names using spaCy
def extract_locations(text):
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ == "GPE"]

# Geocode city names to coordinates
def get_coordinates(city):
    location = geolocator.geocode(city)
    if location:
        return (location.latitude, location.longitude)
    return None

# Check if it's a round trip
def is_round_trip(text):
    text = text.lower()
    return "round trip" in text or "back" in text or "return" in text

# Compute geodesic distance
def compute_distance(city1, city2, round_trip=False):
    coord1 = get_coordinates(city1)
    coord2 = get_coordinates(city2)
    if not coord1 or not coord2:
        raise ValueError("❌ Could not retrieve coordinates for one or both cities.")
    distance = geodesic(coord1, coord2).km
    return distance * 2 if round_trip else distance

# Estimate emissions and suggest better options
def estimate_emissions(text):
    transport = detect_transport(text)
    if not transport:
        return "❌ Transport method not recognized.", None, None

    cities = extract_locations(text)
    if len(cities) < 2:
        return "❌ Could not extract valid city pair.", None, None

    try:
        distance = compute_distance(cities[0], cities[1], round_trip=is_round_trip(text))
    except ValueError as e:
        return str(e), None, None

    emissions = distance * emission_factors[transport]
    message = f"✅ Estimated emissions for the {transport}: **{emissions:.2f} kg CO₂** over **{distance:.2f} km**.  "


    # Alternatives
    alt_emissions = []
    if transport in better_options:
        for alt in better_options[transport]:
            alt_em = emission_factors[alt] * distance
            saving_pct = (emissions - alt_em) / emissions * 100
            if saving_pct > 20:
                message += f"\n💡 You could save **{saving_pct:.1f}% CO₂** ({emissions - alt_em:.2f} kg) by taking a *{alt}* instead.  "
                alt_emissions.append((alt.capitalize(), alt_em))

    original_data = (transport.capitalize(), emissions)
    return message, original_data, alt_emissions

# Plotting emissions comparison
def plot_emissions_comparison(original, alternatives):
    labels = [original[0]] + [alt[0] for alt in alternatives]
    values = [original[1]] + [alt[1] for alt in alternatives]
    colors = ['crimson'] + ['forestgreen'] * len(alternatives)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=colors)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 5, f'{height:.1f} kg', ha='center')

    ax.set_title("CO₂ Emissions Comparison by Transport Mode")
    ax.set_ylabel("Emissions (kg CO₂)")
    ax.set_ylim(0, max(values) * 1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    return fig


# --- Streamlit Interface ---

st.set_page_config(page_title="Carbon Emissions Estimator", page_icon="🌍")

st.title("🌍 Carbon Emissions Estimator")
st.write("Enter a sentence describing your trip, and we'll estimate the CO₂ emissions and suggest greener alternatives!")

example_text = "Flight from Berlin to Stuttgart and back."
user_input = st.text_input("✈️ 🚗 Example: `Flight from Berlin to Stuttgart and back`", value=example_text)

if user_input:
    with st.spinner("Estimating emissions..."):
        msg, original, alternatives = estimate_emissions(user_input)

    st.markdown("### 🔍 Result")
    st.markdown(msg)

    if original and alternatives:
        st.markdown("### 📊 Emissions Comparison")
        fig = plot_emissions_comparison(original, alternatives)
        st.pyplot(fig)
