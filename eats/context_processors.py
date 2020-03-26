from .views.main import get_model_preferences
from .models import Authority, UserProfile


def user_prefs(request):
    """Add the user preferences to the context."""
    try:
        preferences = get_model_preferences(request.user)
    except BaseException:
        preferences = {'authority': None, 'language': None,
                       'script': None, 'calendar': None}
    return {'user_preferences': preferences}


def user_permissions(request):
    """Add a QuerySet of Authority objects that the user is permitted to edit
    to the context."""
    user = request.user
    editable_authorities = Authority.objects.none()
    if user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=user)
            editable_authorities = profile.editable_authorities.all()
        except UserProfile.DoesNotExist:
            pass
    return {'editable_authorities': editable_authorities}
