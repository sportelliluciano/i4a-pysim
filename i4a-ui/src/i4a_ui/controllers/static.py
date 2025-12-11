from fastapi.responses import HTMLResponse

from i4a_ui.app import app


@app.get("/", response_class=HTMLResponse)
def index():
    with open(f"{app.state.assets_dir}/index.html") as f:
        return f.read()


@app.get("/ui/static/{file}", response_class=HTMLResponse)
def index(file: str):
    if file not in ("cytoscape.min.js",):
        return HTMLResponse(status_code=404)

    with open(f"{app.state.assets_dir}/{file}") as f:
        return f.read()
