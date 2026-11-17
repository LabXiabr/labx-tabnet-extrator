import csv
import json
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "tests/fixtures/dados/consolidados"

CSV = BASE / "sia_am_200801_200806.csv"
QUALIDADE = BASE / "sia_am_200801_200806_qualidade.json"


def carregar():
    with CSV.open(encoding="utf-8", newline="") as arquivo:
        registros = list(csv.DictReader(arquivo))

    relatorio = json.loads(
        QUALIDADE.read_text(encoding="utf-8")
    )

    return registros, relatorio


def test_quantidade_de_registros():
    registros, relatorio = carregar()

    assert len(registros) == 159
    assert relatorio["registros"] == len(registros)


def test_seis_competencias():
    registros, _ = carregar()

    contagem = Counter(
        registro["dt_competencia"][:7]
        for registro in registros
    )

    assert contagem == {
        "2008-01": 27,
        "2008-02": 24,
        "2008-03": 27,
        "2008-04": 27,
        "2008-05": 27,
        "2008-06": 27,
    }


def test_sem_duplicidades():
    registros, _ = carregar()

    chaves = [
        (r["sg_uf"], r["dt_competencia"])
        for r in registros
    ]

    assert len(chaves) == len(set(chaves))


def test_total_consolidado():
    registros, relatorio = carregar()

    total = sum(
        int(r["qt_aprovada"])
        for r in registros
    )

    assert total == 245872693
    assert total == relatorio["total_geral"]
    assert (
        relatorio["status"]
        == "consolidado_de_fontes_validadas"
    )
