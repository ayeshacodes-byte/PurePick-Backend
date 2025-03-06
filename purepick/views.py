from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Boycott

@csrf_exempt
def check_boycott(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            
            # Extract the brand name from the received JSON
            brand_name = data.get('brand', None)
            
            if brand_name:
                # Check if the brand exists in the boycott table with partial matching
                boycott_entry = Boycott.objects.filter(boycottcompanyname__icontains=brand_name).first()
                
                if boycott_entry:
                    # If a boycott entry exists for this brand
                    response_data = {
                        'status': 'boycotted',
                        'message': f'The brand "{brand_name}" is boycotted due to: {boycott_entry.reason}.',
                        'country_of_manufacture': boycott_entry.countryofmanufacture
                    }
                else:
                    # If no boycott entry found for this brand
                    response_data = {
                        'status': 'not_boycotted',
                        'message': f'The brand "{brand_name}" is not boycotted.',
                    }
            else:
                # If brand name is missing from the request
                response_data = {
                    'status': 'error',
                    'message': 'No brand provided in the request.',
                }
        except json.JSONDecodeError:
            # Handle invalid JSON format
            response_data = {
                'status': 'error',
                'message': 'Invalid JSON format.',
            }
        return JsonResponse(response_data)
    else:
        # Handle unsupported HTTP methods
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})