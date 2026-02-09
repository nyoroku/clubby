
class UTMTrackingMiddleware:
    """
    Middleware to capture UTM parameters from the URL and store them in the session.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of params to track
        utm_params = ['utm_source', 'utm_medium', 'utm_campaign']
        
        # Check if any UTM param is present in GET
        if any(param in request.GET for param in utm_params):
            # initialize dict if not present
            if 'utm_data' not in request.session:
                request.session['utm_data'] = {}
            
            # Update session with new values
            for param in utm_params:
                value = request.GET.get(param)
                if value:
                    request.session['utm_data'][param] = value
            
            # Mark session as modified
            request.session.modified = True
            
        response = self.get_response(request)
        return response
