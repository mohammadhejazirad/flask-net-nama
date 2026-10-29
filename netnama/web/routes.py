from flask import Blueprint, render_template
from netnama.auth.routes import authenticated

bp = Blueprint("web", __name__)
PAGES = {"overview", "domain_batch", "domain_names", "dns", "ping", "ip", "http", "resources", "about"}


@bp.get("/")
@bp.get("/tools/<page>")
@authenticated
def page(page="overview"):
    from flask import abort

    if page not in PAGES:
        abort(404)
    return render_template("workspace.html", page=page)
