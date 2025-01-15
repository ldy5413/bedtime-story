from .auth import auth_bp

# Add URL prefix for all auth routes
auth_bp.url_prefix = '/auth' 