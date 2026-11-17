import sys
from pathlib import Path

import pytest

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO / "src"))

import inicializar


def test_reutiliza_formulario_existente(
    tmp_path, monkeypatch
):
    modelo = tmp_path / "modelo.json"
    modelo.write_text("{}", encoding="utf-8")

    inspecao = tmp_path / "formulario.json"
    inspecao.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(inicializar, "MODELO", modelo)
    monkeypatch.setattr(inicializar, "INSPECAO", inspecao)

    def nao_executar(*args, **kwargs):
        raise AssertionError("Download indevido")

    monkeypatch.setattr(
        inicializar.subprocess,
        "run",
        nao_executar,
    )

    inicializar.main()


def test_inicializa_quando_formulario_ausente(
    tmp_path, monkeypatch
):
    modelo = tmp_path / "modelo.json"
    modelo.write_text("{}", encoding="utf-8")

    inspecao = tmp_path / "formulario.json"

    monkeypatch.setattr(inicializar, "MODELO", modelo)
    monkeypatch.setattr(inicializar, "INSPECAO", inspecao)

    def executar_simulado(*args, **kwargs):
        inspecao.write_text(
            '{"formularios": [], "campos": []}',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        inicializar.subprocess,
        "run",
        executar_simulado,
    )

    inicializar.main()

    assert inspecao.is_file()


def test_bloqueia_modelo_ausente(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        inicializar,
        "MODELO",
        tmp_path / "modelo_ausente.json",
    )

    with pytest.raises(
        SystemExit, match="Modelo de consulta ausente"
    ):
        inicializar.main()
