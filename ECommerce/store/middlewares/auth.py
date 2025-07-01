from django.shortcuts import redirect
from functools import wraps

def session_auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('customer'):
            return redirect(f'/login?return_url={request.path}')
        return view_func(request, *args, **kwargs)
    return _wrapped_view