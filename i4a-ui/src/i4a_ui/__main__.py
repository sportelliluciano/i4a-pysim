import uvicorn

from i4a_ui.app import app
import i4a_ui.controllers as _


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")


main()
