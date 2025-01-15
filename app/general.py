from flask import Blueprint, render_template
from app.auth.auth import login_required

general_bp = Blueprint('general', __name__)

@general_bp.route('/')
@login_required
def index():
    return render_template('index.html')