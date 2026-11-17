import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "core"))

from montar_consulta import montar_consulta

import montar_consulta as modulo_montagem
import selecionar_fonte as modulo_fonte
import validar_catalogo as modulo_catalogo


@pytest.fixture(autouse=True)
def ambiente_consulta_isolado(tmp_path, monkeypatch):
    catalogo = json.loads(
        (RAIZ / "configuracoes/fontes.json").read_text(
            encoding="utf-8"
        )
    )

    fonte = catalogo["fontes"]["SIA/AM"]

    fonte["inspecao_local"] = (
        "dados/inspecao/formulario_sia_qabr.json"
    )
    fonte["modelo_local"] = (
        "configuracoes/modelos/sia_am_base.json"
    )

    caminho_catalogo = (
        tmp_path / "configuracoes/fontes.json"
    )
    caminho_catalogo.parent.mkdir(
        parents=True, exist_ok=True
    )
    caminho_catalogo.write_text(
        json.dumps(catalogo, ensure_ascii=False),
        encoding="utf-8",
    )

    modelo_original = (
        RAIZ / "configuracoes/modelos/sia_am_base.json"
    )
    modelo_destino = (
        tmp_path / fonte["modelo_local"]
    )
    modelo_destino.parent.mkdir(
        parents=True, exist_ok=True
    )
    modelo_destino.write_bytes(
        modelo_original.read_bytes()
    )

    formulario = {
        "campos": [
            {
                "name": "Arquivos",
                "opcoes": [
                    {"value": "qabr0803.dbf"}
                ],
            }
        ]
    }

    caminho_formulario = (
        tmp_path / fonte["inspecao_local"]
    )
    caminho_formulario.parent.mkdir(
        parents=True, exist_ok=True
    )
    caminho_formulario.write_text(
        json.dumps(formulario),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        modulo_montagem, "RAIZ", tmp_path
    )
    monkeypatch.setattr(
        modulo_catalogo, "RAIZ", tmp_path
    )
    monkeypatch.setattr(
        modulo_fonte, "CATALOGO", caminho_catalogo
    )


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

    arquivo = RAIZ / "tests/fixtures/dados/consultas/sia_am_200803.json"

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
