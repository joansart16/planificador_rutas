class ModuleSessionMiddleware:
    """Sets current_module in session automatically based on the URL prefix."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith('/obra/'):
            request.session['current_module'] = 'OBRA'
        elif path.startswith('/evento/'):
            request.session['current_module'] = 'EVENTO'
        return self.get_response(request)
