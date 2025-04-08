import base64
from venv import logger
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Boycott, Alternateproducts

CATEGORY_MAPPING = {
    "Beverages": "Drinks",
    "Body Wash": "Washing detergent",
    # Add other mappings if needed
}

@csrf_exempt
def check_boycott(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Received data: {data}")  # Debugging Log
            brand_name = data.get('brand', None)

            if brand_name:
                boycott_entry = Boycott.objects.filter(boycottcompanyname__icontains=brand_name).first()
                
                if boycott_entry:
                    response_data = {
                        'status': 'boycotted',
                        'message': f'The brand "{brand_name}" is boycotted due to: {boycott_entry.reason}.',
                        'country_of_manufacture': boycott_entry.countryofmanufacture
                    }

                    # Fetch alternative products related to the brand
                    alternative_products = Alternateproducts.objects.filter(alternateproductcompany__icontains=brand_name)

                    alternatives_list = []
                    for alt in alternative_products:
                        # Handle BinaryField for image
                        image_base64 = base64.b64encode(alt.alternateproductimage).decode('utf-8') if alt.alternateproductimage else None

                        alternatives_list.append({
                            'alternative_product': alt.alternateproductname,
                            'alternative_company': alt.alternatecompanyname,
                            'image_base64': image_base64  # Include Base64-encoded image
                        })

                    response_data['alternatives'] = alternatives_list if alternatives_list else 'No direct alternatives found.'
                else:
                    response_data = {
                        'status': 'not_boycotted',
                        'message': f'The brand "{brand_name}" is not boycotted.',
                    }
            else:
                response_data = {'status': 'error', 'message': 'No brand provided in the request.'}

        except json.JSONDecodeError:
            response_data = {'status': 'error', 'message': 'Invalid JSON format.'}

        return JsonResponse(response_data)
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    

# ✅ New View for Alternative Products by Category
@csrf_exempt
def get_alternatives(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            category_name = data.get('category', None)

            if category_name:
                # Use the mapping to translate the category name
                category_name = CATEGORY_MAPPING.get(category_name, category_name)

                # Fetch alternative products based on the mapped category
                alternative_products = Alternateproducts.objects.filter(
                    alternatecategory__categoryid__categoryname__icontains=category_name
                )

                alternatives_list = []
                for alt in alternative_products:
                    # Handle BinaryField for image
                    image_base64 = base64.b64encode(alt.alternateproductimage).decode('utf-8') if alt.alternateproductimage else None

                    alternatives_list.append({
                        'alternative_product': alt.alternateproductname,
                        'alternative_company': alt.alternatecompanyname,
                        'image_base64': image_base64
                    })

                return JsonResponse({'status': 'success', 'alternatives': alternatives_list})

            else:
                return JsonResponse({'status': 'error', 'message': 'No category provided.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'})

    return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})



################# ALLERGEN DETECTION ########################
import json
import logging
import os
import faiss
import pandas as pd
import numpy as np
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re

# ✅ Configure Google Gemini API
genai.configure(api_key="AIzaSyB22EL4EX5up1HEJY66Eu1dHfkSUV5D6VY")  # Replace with actual API key
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# ✅ Load FAISS index and allergen database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
faiss_index_path = os.path.join(BASE_DIR, "allergen_index.faiss")
csv_path = os.path.join(BASE_DIR, "allergen_database.csv")

if os.path.exists(faiss_index_path) and os.path.exists(csv_path):
    logging.info("✅ Loading FAISS index and allergen database...")
    index = faiss.read_index(faiss_index_path)
    allergen_df = pd.read_csv(csv_path)
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    logging.info("✅ FAISS index and database loaded successfully.")
else:
    logging.error("❌ FAISS index or database not found. Please run train_faiss.py first.")
    index = None
    allergen_df = None
    embedder = None

def normalize_text(text):
    """Remove unnecessary descriptors and format text for better allergen detection."""
    text = text.lower()
    text = re.sub(r"\b(organic|natural|raw|fresh|pure|non-gmo|unsalted|roasted)\b", "", text)
    text = re.sub(r"[\(\)]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

@csrf_exempt
def check_allergen(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_input = data.get("query", "").strip()

        if not user_input:
            return JsonResponse({"error": "Query cannot be empty"}, status=400)

        if index is None or allergen_df is None or embedder is None:
            return JsonResponse({"error": "Server not initialized properly."}, status=500)

        # ✅ Convert user input to embedding
        query_embedding = embedder.encode([user_input])

        # ✅ Search FAISS for the closest match
        D, I = index.search(np.array(query_embedding), k=1)  # Top-1 match

        if I[0][0] == -1 or I.size == 0:
            return JsonResponse({"response": "No matching allergen found."})

        # ✅ Retrieve allergen data from FAISS
        matched_data = allergen_df.iloc[I[0][0]].to_dict()

        # ✅ Normalize input and database ingredients
        user_ingredients = set(normalize_text(user_input).split(", "))
        matched_ingredients = set(normalize_text(matched_data["Ingredients"]).split(", "))

        # ✅ Find allergens using substring matching
        detected_allergens = set()
        for allergen in matched_data["Allergens"].split(", "):
            allergen = allergen.strip()
            for ingredient in user_ingredients:
                if allergen in ingredient or ingredient in allergen:
                    detected_allergens.add(allergen)

        # ✅ Ensure allergy names end with "allergy"
        allergy_mapping = dict(zip(matched_data["Allergens"].split(", "), matched_data["Allergy name"].split(", ")))
        detected_allergy_names = set()
        for allergen in detected_allergens:
            allergy_name = allergy_mapping.get(allergen, allergen)
            if "allergy" not in allergy_name.lower():
                detected_allergy_names.add(f"{allergy_name} allergy")
            else:
                detected_allergy_names.add(allergy_name)

        # ✅ Use Gemini AI to validate and refine detection
        gemini_prompt = f"""
        Given the detected ingredients: "{user_input}" and the closest allergen data from FAISS: "{matched_data['Ingredients']}", verify and refine the allergen detection.
        Only include allergens that exist in both the query and FAISS match.
        Respond **strictly in JSON format** with no extra text. The output **must** match this format:
        {{
            "Ingredients": "{user_input}",
            "Allergy name": "{', '.join(sorted(detected_allergy_names))}",
            "Allergens": "{', '.join(sorted(detected_allergens))}"
        }}
        """

        gemini_response = model.generate_content(gemini_prompt)

        # ✅ Extract response text
        if not hasattr(gemini_response, "text") or not gemini_response.text.strip():
            logging.error("❌ Gemini returned an empty response.")
            return JsonResponse({"error": "AI model failed to generate a valid response."}, status=500)

        response_text = gemini_response.text.strip()
        logging.info(f"✅ Gemini Raw Response: {response_text}")

        # ✅ Extract JSON using regex
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not json_match:
            logging.error("❌ Gemini did not return a valid JSON response.")
            return JsonResponse({"error": "AI model failed to generate a valid response."}, status=500)

        json_string = json_match.group(0)  # Extract JSON part
        logging.info(f"✅ Extracted JSON: {json_string}")

        # ✅ Validate and parse JSON response from Gemini
        try:
            gemini_output = json.loads(json_string)
            return JsonResponse({"response": gemini_output})
        except json.JSONDecodeError:
            logging.error("❌ Error: Extracted JSON is invalid.")
            return JsonResponse({"error": "AI model failed to generate a valid response."}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON input."}, status=400)
    except Exception as e:
        logging.error(f"❌ Error in check_allergen: {str(e)}")
        return JsonResponse({"error": "Internal Server Error"}, status=500)