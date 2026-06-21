# Carbon Footprint Calculator Engine

# Emission factors (in kg CO2)
TRANSPORT_FACTORS = {
    'gasoline_car': 0.411,     # kg CO2 per mile
    'electric_car': 0.110,     # kg CO2 per mile (based on US average electricity grid)
    'public_transit': 0.140,   # kg CO2 per passenger mile
    'flight': 0.240,           # kg CO2 per passenger mile
    'active': 0.0              # walking/cycling
}

ELECTRICITY_FACTOR = 0.390     # kg CO2 per kWh

DIET_FACTORS = {
    'vegan': 2.9,              # kg CO2 per day
    'vegetarian': 3.8,         # kg CO2 per day
    'average': 5.6,            # kg CO2 per day
    'meat_heavy': 7.2          # kg CO2 per day
}

def calculate_footprint(transport_miles, transport_type, electricity_kwh, diet_type):
    """
    Calculates carbon footprint in kg CO2.
    Returns:
        dict: Breakdown of emissions and total.
    """
    # Calculate transport emissions
    t_factor = TRANSPORT_FACTORS.get(transport_type, 0.0)
    transport_emissions = float(transport_miles) * t_factor

    # Calculate electricity emissions
    electricity_emissions = float(electricity_kwh) * ELECTRICITY_FACTOR

    # Calculate diet emissions
    diet_emissions = DIET_FACTORS.get(diet_type, 5.6)

    # Calculate total
    total_emissions = transport_emissions + electricity_emissions + diet_emissions

    return {
        'transport': round(transport_emissions, 2),
        'electricity': round(electricity_emissions, 2),
        'diet': round(diet_emissions, 2),
        'total': round(total_emissions, 2)
    }
