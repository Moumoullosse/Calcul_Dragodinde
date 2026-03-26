from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.data import BREEDS, SESSION_INDIVIDUAL_CAPACITY
from core.planner import StockEntry, default_stock, plan_session


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Planificateur Dragodindes")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _stock_from_form(form_data: dict[str, str]) -> dict[str, StockEntry]:
    stock = default_stock()
    for breed in BREEDS:
        males = int(form_data.get(f"m_{breed.name}", 0) or 0)
        females = int(form_data.get(f"f_{breed.name}", 0) or 0)
        stock[breed.name] = StockEntry(males=males, females=females)
    return stock


def _serialize_results(results: dict[str, object]) -> dict[str, object]:
    selection_rows = [asdict(row) for row in results["selection_rows"]]
    return {
        **results,
        "selection_rows": selection_rows,
    }


def _render(request: Request, stock: dict[str, StockEntry], session_capacity: int) -> HTMLResponse:
    results = _serialize_results(plan_session(stock, session_capacity))
    stock_rows = [
        {
            "name": breed.name,
            "generation": breed.generation,
            "males": stock[breed.name].males,
            "females": stock[breed.name].females,
        }
        for breed in BREEDS
    ]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "stock_rows": stock_rows,
            "session_capacity": session_capacity,
            "results": results,
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _render(request, default_stock(), SESSION_INDIVIDUAL_CAPACITY)


@app.post("/", response_class=HTMLResponse)
async def calculate(
    request: Request,
    session_capacity: int = Form(SESSION_INDIVIDUAL_CAPACITY),
) -> HTMLResponse:
    form = await request.form()
    stock = _stock_from_form(dict(form))
    return _render(request, stock, session_capacity)
