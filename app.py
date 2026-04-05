import streamlit as st
from google import genai
import json
import os
import re
from typing import List, Dict, Optional

# --- Page Config ---
st.set_page_config(
    page_title="Aaj Kya Banaye - AI Meal Planner",
    page_icon="🍳",
    layout="wide"
)

# --- Styling ---
st.markdown("""
    <style>
    .main { background-color: #faf9f6; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #ff4b2b;
        color: white;
        font-weight: bold;
    }
    .recipe-card {
        background-color: white;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #eee;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API Setup ---
api_key = st.secrets.get("GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("Please set GEMINI_API_KEY in Streamlit Secrets or Environment Variables.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

# --- Helper Functions ---

def extract_json(text: str):
    """Robustly extracts JSON from LLM response even if it contains markdown or chatter."""
    # Strip markdown code fences
    text = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: find JSON array or object
    try:
        match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', text)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        st.error(f"JSON Parsing Error: {e}")
    return None


def get_meal_suggestions(cuisine: str, dietary_type: str, meal_type: str, other_prefs: str) -> List[Dict]:
    prompt = f"""
    Suggest 6 delicious meal options for someone who wants to eat {cuisine} cuisine for {meal_type}.
    The person follows a {dietary_type} diet.
    Other preferences: {other_prefs if other_prefs else "None"}.

    Return ONLY a JSON array of objects with these exact keys:
    "name": Name of the dish
    "description": Brief appetizing description (1-2 sentences)
    "cuisine": "{cuisine}"
    "dietaryType": "{dietary_type}"
    "mealType": "{meal_type}"

    Do not include any explanation, markdown, or code fences. Return raw JSON only.
    """
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        data = extract_json(response.text)
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Error fetching suggestions: {e}")
        return []


def get_recipe_details(meal_name: str, cuisine: str, dietary_type: str, meal_type: str) -> Optional[Dict]:
    prompt = f"""
    Provide a detailed recipe for "{meal_name}" ({cuisine} cuisine, {dietary_type}, {meal_type}).

    Return ONLY a JSON object with these exact keys:
    "name": Name of the dish (string)
    "ingredients": List of ingredient strings
    "instructions": List of step strings
    "tips": List of tip strings
    "difficulty": One of "Easy", "Medium", or "Hard"
    "prepTime": Preparation time as a string e.g. "10 mins"
    "cookTime": Cooking time as a string e.g. "20 mins"
    "servings": Number of servings as a string e.g. "4"
    "nutritionalHighlights": One sentence highlight string

    Do not include any explanation, markdown, or code fences. Return raw JSON only.
    """
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return extract_json(response.text)
    except Exception as e:
        st.error(f"Error fetching recipe: {e}")
        return None


# --- Session State Initialization ---
if 'view' not in st.session_state:
    st.session_state.view = 'home'
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = []
if 'recipe' not in st.session_state:
    st.session_state.recipe = None
if 'selected_cuisine' not in st.session_state:
    st.session_state.selected_cuisine = 'Punjabi'
if 'selected_dietary' not in st.session_state:
    st.session_state.selected_dietary = 'Veg'
if 'selected_meal_type' not in st.session_state:
    st.session_state.selected_meal_type = 'Lunch'

# --- UI Layout ---
st.title("🍳 Aaj Kya Banaye")
st.subheader("AI-Powered Meal Suggestions & Recipes")

with st.sidebar:
    st.header("Your Preferences")
    cuisine = st.selectbox(
        "Cuisine",
        ['Punjabi', 'South Indian', 'Gujarati', 'Rajasthani', 'Bengali',
         'Maharashtrian', 'Chinese', 'Italian', 'Mexican', 'Continental']
    )
    meal_type = st.selectbox(
        "Meal Type",
        ['Breakfast', 'Brunch', 'Lunch', 'Evening Snack', 'Dinner']
    )
    dietary_type = st.selectbox(
        "Dietary Type",
        ['Veg', 'Non-Veg', 'Jain', 'Vegan', 'Eggitarian']
    )
    other_prefs = st.text_area(
        "Other Preferences",
        placeholder="e.g. Spicy, low carb, quick to make..."
    )

    if st.button("🍽️ Suggest Meals"):
        st.session_state.selected_cuisine = cuisine
        st.session_state.selected_dietary = dietary_type
        st.session_state.selected_meal_type = meal_type
        with st.spinner("Chef is thinking..."):
            res = get_meal_suggestions(cuisine, dietary_type, meal_type, other_prefs)
            if res:
                st.session_state.suggestions = res
                st.session_state.view = 'suggestions'
                st.rerun()
            else:
                st.warning("No suggestions returned. Please try again.")

# --- Main Content ---

if st.session_state.view == 'suggestions':
    st.markdown(f"### 🍴 Today's {st.session_state.selected_meal_type} Specials")
    st.caption(f"{st.session_state.selected_cuisine} · {st.session_state.selected_dietary}")

    cols = st.columns(2)
    for idx, meal in enumerate(st.session_state.suggestions):
        with cols[idx % 2]:
            st.markdown(f"""
                <div class="recipe-card">
                    <h4>{meal.get('name', 'Unknown Dish')}</h4>
                    <p style="color:#555;">{meal.get('description', '')}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("View Recipe →", key=f"btn_{idx}"):
                with st.spinner(f"Preparing {meal.get('name', 'recipe')}..."):
                    recipe = get_recipe_details(
                        meal['name'],
                        st.session_state.selected_cuisine,
                        st.session_state.selected_dietary,
                        st.session_state.selected_meal_type
                    )
                    if recipe:
                        st.session_state.recipe = recipe
                        st.session_state.view = 'recipe'
                        st.rerun()
                    else:
                        st.warning("Could not load recipe. Please try again.")

elif st.session_state.view == 'recipe' and st.session_state.recipe:
    recipe = st.session_state.recipe

    if st.button("← Back to Suggestions"):
        st.session_state.view = 'suggestions'
        st.rerun()

    st.header(f"🍛 {recipe.get('name', 'Recipe')}")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⚡ Difficulty", recipe.get('difficulty', 'N/A'))
    col2.metric("⏱️ Prep Time", recipe.get('prepTime', 'N/A'))
    col3.metric("🔥 Cook Time", recipe.get('cookTime', 'N/A'))
    col4.metric("🍽️ Servings", recipe.get('servings', 'N/A'))

    # Nutritional highlight
    if recipe.get('nutritionalHighlights'):
        st.info(f"🥗 **Nutritional Highlights:** {recipe['nutritionalHighlights']}")

    st.write("")

    # Ingredients + Instructions
    ing_col, inst_col = st.columns([1, 2])

    with ing_col:
        st.write("### 🛒 Ingredients")
        for item in recipe.get('ingredients', []):
            st.write(f"- {item}")

    with inst_col:
        st.write("### 👨‍🍳 Instructions")
        for i, step in enumerate(recipe.get('instructions', []), start=1):
            st.write(f"**{i}.** {step}")

    # Tips
    tips = recipe.get('tips', [])
    if tips:
        st.write("---")
        st.write("### 💡 Pro Tips")
        for tip in tips:
            st.write(f"- {tip}")

    # YouTube search link
    st.write("---")
    st.write("### 📺 Video Tutorials")
    recipe_name = recipe.get('name', '')
    search_query = recipe_name.replace(' ', '+') + '+recipe'
    youtube_url = f"https://www.youtube.com/results?search_query={search_query}"
    st.markdown(f"🔍 [Search **{recipe_name}** on YouTube]({youtube_url})")

else:
    st.info("👈 Select your preferences in the sidebar and click **'Suggest Meals'** to get started!")
    st.markdown("""
        ### How it works:
        1. 🎯 Pick your **cuisine**, **meal type**, and **dietary preference**
        2. ✨ Add any **other preferences** (spicy, quick, low-carb...)
        3. 🍽️ Click **Suggest Meals** and get 6 AI-generated options
        4. 📖 Click any dish to see the **full recipe with tips**
    """)