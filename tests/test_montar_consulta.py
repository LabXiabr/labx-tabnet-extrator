import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "core"))

from montar_consulta import montar_consulta


def parametros(consulta):
    return consulta["parametros"]


def test_monta_marco_2008():
    consulta = montar_consulta("SIA", "AM", "2008-03")

    arquivos = [
        valor
        for nome, valor in parametros(consulta)
        if nome == "Arquivos"
    ]

    assert arquivos == ["qabr0803.dbf"]
    assert consulta["status"] == "gerada_em_memoria"


def test_equivalencia_com_consulta_validada():
    gerada = montar_consulta("SIA", "AM", "2008-03")

    arquivo = RAIZ / "dados/consultas/sia_am_200803.json"

    original = json.loads(
        arquivo.read_text(encoding="utf-8")
    )

    assert gerada["parametros"] == original["parametros"]


def test_rejeita_competencia_indisponivel():
    with pytest.raises(
        ValueError, match="Competencia indisponivel"
    ):
        montar_consulta("SIA", "AM", "2007-12")


def test_rejeita_fonte_nao_cadastrada():
    with pytest.raises(
        ValueError, match="Fonte nao cadastrada"
    ):
        montar_consulta("SIH", "RD", "2008-03")
