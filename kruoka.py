import logging
import zoneinfo
from datetime import datetime, timedelta

from flask import Flask, abort, jsonify
from playwright.sync_api import sync_playwright
from werkzeug.exceptions import HTTPException

timezone = zoneinfo.ZoneInfo("Europe/Helsinki")


class API(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_error_handler(HTTPException, self.error_handler)

    def error_handler(self, e):
        return {"title": f"{e.code}: {e.name}"}, e.code


api = API(__name__)


cache = {}


def parse_date(s):
    year = str(datetime.now(timezone).year)
    parsed = datetime.strptime(s.split()[-1] + year, "%d.%m.%Y").replace(
        tzinfo=timezone
    )
    return parsed.date()


def parse_times(s):
    (opens, closes) = (x.replace(".", ":") for x in s.split("–"))
    return (opens, closes)


def fetch_data():
    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page()
        page.goto("https://www.k-ruoka.fi/kauppa/k-market-tuira/aukioloajat")
        for entry in page.get_by_test_id("opening-hours-row").all():
            day = parse_date(entry.get_by_test_id("opening-hours-label").inner_text())
            (opens, closes) = parse_times(
                entry.get_by_test_id("opening-hours-hours").inner_text()
            )
            cache[str(day)] = {"opens": opens, "closes": closes}


@api.route("/", defaults={"isodate": None}, methods=["GET"])
@api.route("/<isodate>", methods=["GET"])
def handler(isodate):
    if isodate is None:
        query = datetime.now(timezone).date()
    else:
        try:
            query = datetime.strptime(isodate, "%Y-%m-%d").replace(tzinfo=timezone).date()
        except ValueError:
            api.logger.warning(f"Invalid date {query!r}")
            abort(400)

    if str(query) not in cache:
        if query < datetime.now(timezone).date():
            api.logger.warning(f"Cannot query past dates ({query!r}) from source")
            abort(404)
        elif query > datetime.now(timezone).date() + timedelta(days=7):
            api.logger.warning(
                f"Cannot query dates newer than 7 days ({query!r}) from source"
            )
            abort(404)
        fetch_data()
    try:
        return jsonify(cache[str(query)])
    except KeyError:
        abort(404)


if __name__ == "__main__":
    api.run(host="127.0.0.1", port=8000, debug=True)
else:
    gunicorn_logger = logging.getLogger("gunicorn.error")
    api.logger.handlers = gunicorn_logger.handlers
    api.logger.setLevel(gunicorn_logger.level)
