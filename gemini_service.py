import os
import json
import logging
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    logger.info("Gemini API configured successfully.")
else:
    logger.warning("GEMINI_API_KEY environment variable not found. Using local fallback generator.")

def get_fallback_recommendations(stats):
    """
    Generate local fallback recommendations based on stats.
    stats = {
        'avg_transport_miles': float,
        'avg_electricity_kwh': float,
        'predominant_transport_type': str,
        'predominant_diet_type': str,
        'avg_emissions': float,
        'daily_goal': float
    }
    """
    recommendations = []
    
    # 1. Transportation suggestions
    if stats.get('avg_transport_miles', 0) > 10:
        if stats.get('predominant_transport_type') == 'gasoline_car':
            recommendations.append({
                'category': 'transportation',
                'suggestion': 'Try public transit or carpooling for commutes to cut travel emissions in half.'
            })
        elif stats.get('predominant_transport_type') == 'flight':
            recommendations.append({
                'category': 'transportation',
                'suggestion': 'Reduce flights by opting for virtual meetings or train travel where possible.'
            })
    if len(recommendations) < 1 and stats.get('predominant_transport_type') != 'active':
        recommendations.append({
            'category': 'transportation',
            'suggestion': 'Walk or cycle for short errands under 2 miles instead of driving.'
        })

    # 2. Electricity suggestions
    if stats.get('avg_electricity_kwh', 0) > 8:
        recommendations.append({
            'category': 'electricity',
            'suggestion': 'Unplug vampire devices (chargers, gaming consoles) when not in use.'
        })
        recommendations.append({
            'category': 'electricity',
            'suggestion': 'Switch home lighting to high-efficiency LED bulbs to save electricity.'
        })
    else:
        recommendations.append({
            'category': 'electricity',
            'suggestion': 'Wash laundry in cold water to save up to 90% of the machine\'s energy.'
        })

    # 3. Diet suggestions
    diet = stats.get('predominant_diet_type', 'average')
    if diet == 'meat_heavy':
        recommendations.append({
            'category': 'diet',
            'suggestion': 'Swap beef or pork for plant-based proteins (beans, tofu) at least three days a week.'
        })
    elif diet == 'average':
        recommendations.append({
            'category': 'diet',
            'suggestion': 'Adopt "Meatless Mondays" to easily transition into a lower-impact diet.'
        })
    else:
        recommendations.append({
            'category': 'diet',
            'suggestion': 'Source local, seasonal organic produce to decrease transport emissions of food.'
        })

    # Limit to 3 recommendations
    return recommendations[:3]

def generate_recommendations(stats):
    """
    Generate recommendations using Gemini if configured, else fall back to local rule-based recommendations.
    """
    if not api_key:
        return get_fallback_recommendations(stats)

    prompt = f"""
    You are an eco-friendly AI assistant helper.
    A user is tracking their carbon footprint. Here is their profile data and averages for the past week:
    - Average daily transportation distance: {stats.get('avg_transport_miles', 0):.2f} miles
    - Predominant transportation mode: {stats.get('predominant_transport_type', 'unknown')}
    - Average daily home electricity: {stats.get('avg_electricity_kwh', 0):.2f} kWh
    - Diet style: {stats.get('predominant_diet_type', 'average')}
    - Average daily carbon footprint: {stats.get('avg_emissions', 0):.2f} kg CO2
    - Set daily emissions goal: {stats.get('daily_goal', 20):.2f} kg CO2

    Based on this data, provide 3 highly relevant, specific, and actionable eco-friendly recommendations.
    Return the response as a raw JSON array of objects. Do not wrap in backticks or markdown, do not write anything else.
    Each object in the array MUST have exactly these two fields:
    - "category": must be exactly one of "transportation", "electricity", or "diet"
    - "suggestion": a short, encouraging action item (maximum 15 words)

    Example format:
    [
      {{"category": "transportation", "suggestion": "Carpool to work twice a week to lower gasoline usage."}},
      ...
    ]
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown code block wraps if the LLM returned them despite instructions
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                text = "\n".join(lines[1:-1])
        
        data = json.loads(text.strip())
        if isinstance(data, list) and len(data) > 0:
            # Validate format
            validated = []
            for item in data:
                cat = item.get('category', 'lifestyle')
                sug = item.get('suggestion')
                if sug:
                    validated.append({
                        'category': cat if cat in ['transportation', 'electricity', 'diet'] else 'electricity',
                        'suggestion': sug[:120]  # limit length
                    })
            if validated:
                return validated[:3]
    except Exception as e:
        logger.error(f"Failed to generate recommendations using Gemini: {e}")
        
    # Fallback if exception or invalid response structure
    return get_fallback_recommendations(stats)
