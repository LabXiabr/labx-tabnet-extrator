import csv
from pathlib import Path

ARQUIVO = Path("dados/saida/sia_am_200801.csv")


def carregar_registros():
    with ARQUIVO.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_total_de_ufs():
    registros = carregar_registros()
    assert len(registros) == 27
    assert len({r["sg_uf"] for r in registros}) == 27


def test_competencia():
    registros = carregar_registros()
    assert all(
        r["dt_competencia"] == "2008-01-01"
        for r in registros
    )


def test_total_nacional():
    registros = carregar_registros()
    total = sum(int(r["qt_aprovada"]) for r in registros)
    assert total == 36088068


def test_rondonia():
    registros = carregar_registros()
    valores = {
        r["sg_uf"]: int(r["qt_aprovada"])
        for r in registros
    }
    assert valores["RO"] == 35943
