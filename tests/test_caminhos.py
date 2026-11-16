import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from core.caminhos import nome_execucao


def test_nome_sia_am():
    assert nome_execucao(
        "SIA", "AM", "2008-03"
    ) == "sia_am_200803"


def test_nome_sih_rd():
    assert nome_execucao(
        "SIH", "RD", "2024-12"
    ) == "sih_rd_202412"


def test_normaliza_maiusculas():
    assert nome_execucao(
        "sia", "am", "2008-01"
    ) == "sia_am_200801"


def test_rejeita_competencia_invalida():
    with pytest.raises(ValueError):
        nome_execucao("SIA", "AM", "2008-13")


def test_rejeita_identificador_inseguro():
    with pytest.raises(ValueError):
        nome_execucao("../SIA", "AM", "2008-03")
