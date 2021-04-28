from pathlib import Path
import importlib.resources as pkg_resources

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .__version__ import __version__
from . import templates
from .collectors import handle_collectd


app = FastAPI()

with pkg_resources.path(templates, "index.html.jinja") as template_file:
    templates = Jinja2Templates(directory=template_file.parent)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    figure_map = handle_collectd(Path("/var/lib/collectd/"))

    return templates.TemplateResponse(
        "index.html.jinja",
        {"request": request, "version": __version__, "figure_map": figure_map},
    )
