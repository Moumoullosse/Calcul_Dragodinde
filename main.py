from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
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


def _build_export_content(
    stock: dict[str, StockEntry],
    session_capacity: int,
    include_auto_fill_g1: bool,
) -> str:
    results = plan_session(stock, session_capacity, include_auto_fill_g1)

    lines = [
        "Resume planificateur Dragodindes",
        f"Genere le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Parametres",
        f"- Capacite de session : {session_capacity}",
        f"- Remplissage automatique Gen 1 : {'Oui' if include_auto_fill_g1 else 'Non'}",
        "",
        "Controle",
    ]

    for key, value in results["controls"].items():
        lines.append(f"- {key} : {value}")

    lines.extend(["", "Stock a prendre"])
    plan_rows = results["plan_rows"]
    if plan_rows:
        for row in plan_rows:
            lines.extend(
                [
                    f"- {row['Dragodinde']} (Gen {row['Gen']})",
                    f"  Males a prendre : {row['Males a prendre']}",
                    f"  Femelles a prendre : {row['Femelles a prendre']}",
                    f"  Paires prises : {row['Paires prises']}",
                ]
            )
    else:
        lines.append("- Aucun stock a prendre pour cette configuration.")

    lines.extend(["", "Couples crees"])
    recap_rows = results["recap_creation_rows"]
    if recap_rows:
        for row in recap_rows:
            lines.extend(
                [
                    f"- {row['Dragodinde creee']} (Gen {row['Gen']})",
                    f"  Parents : {row['Parent 1']} + {row['Parent 2']}",
                    f"  Mode retenu : {row['Mode retenu']}",
                    f"  Paires creees : {row['Paires creees']}",
                ]
            )
    else:
        lines.append("- Aucun couple cree avec ce stock.")

    lines.extend(["", "Stock saisi"])
    for breed in BREEDS:
        entry = stock[breed.name]
        if entry.males > 0 or entry.females > 0:
            lines.append(
                f"- {breed.name} (Gen {breed.generation}) : {entry.males} male(s), {entry.females} femelle(s)"
            )

    return "\n".join(lines) + "\n"


def _render(
    request: Request,
    stock: dict[str, StockEntry],
    session_capacity: int,
    include_auto_fill_g1: bool,
) -> HTMLResponse:
    results = _serialize_results(plan_session(stock, session_capacity, include_auto_fill_g1))
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
            "include_auto_fill_g1": include_auto_fill_g1,
            "results": results,
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _render(request, default_stock(), SESSION_INDIVIDUAL_CAPACITY, True)


@app.post("/", response_class=HTMLResponse)
async def calculate(
    request: Request,
    session_capacity: int = Form(SESSION_INDIVIDUAL_CAPACITY),
) -> HTMLResponse:
    form = await request.form()
    form_data = dict(form)
    stock = _stock_from_form(form_data)
    include_auto_fill_g1 = "include_auto_fill_g1" in form_data
    return _render(request, stock, session_capacity, include_auto_fill_g1)


@app.post("/download-summary")
async def download_summary(
    session_capacity: int = Form(SESSION_INDIVIDUAL_CAPACITY),
) -> PlainTextResponse:
    form = await request.form()
    form_data = dict(form)
    stock = _stock_from_form(form_data)
    include_auto_fill_g1 = "include_auto_fill_g1" in form_data
    content = _build_export_content(stock, session_capacity, include_auto_fill_g1)
    filename = f"resume_dragodindes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(content, headers=headers)
