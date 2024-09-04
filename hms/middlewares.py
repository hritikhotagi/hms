import requests
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.middleware import get_user as default_get_user


class Auth0Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Apply authorization only to /api routes
        if request.path.startswith('/api/'):
            access_token = None

            # First check if the access token is in the session
            access_token = request.session.get('access_token', None)
            if not access_token:
                # If not in session, check Authorization header
                auth_header = request.headers.get('Authorization', None)
                if auth_header:
                    try:
                        token_type, access_token = auth_header.split()
                        if token_type != 'Bearer':
                            return JsonResponse({'error': 'Invalid authorization header format'}, status=401)
                    except ValueError:
                        return JsonResponse({'error': 'Invalid authorization header format'}, status=401)

            # No access token found in session or header
            if not access_token:
                return JsonResponse({'error': 'Authorization required'}, status=401)

            # Validate token with Auth0 /userinfo
            user_info_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
            headers = {'Authorization': f"Bearer {access_token}"}
            response = requests.get(user_info_url, headers=headers)

            if response.status_code != 200:
                return JsonResponse({'error': 'Invalid token'}, status=401)

            # Auth0 user info is valid
            auth0_user = response.json()

            # Check if the user exists in Django, if not, create it
            email = auth0_user['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user if not found
                user = User.objects.create_user(username=email.split('@')[0], email=email)
                user.save()

            # Ensure that the user is set in request
            request.user = SimpleLazyObject(lambda: user)
            request.auth0_user = auth0_user

            # print("Authenticated user:", request.user.is_authenticated)
        else:
            # If it's not an API route, use the default behavior
            request.user = default_get_user(request)

        return self.get_response(request)

