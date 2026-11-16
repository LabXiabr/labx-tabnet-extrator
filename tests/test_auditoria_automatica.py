import json
import sys
from pathlib import Path

import pytest

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO / "src"))

import executar_intervalo as intervalo
from auditoria.manifesto_competencia import (
    gerar_manifesto_competencia,
)


def preparar_arquivos(raiz):
    pasta = raiz / "dados/execucoes/sia_am_200902"
    pasta.mkdir(parents=True)

    html = raiz / "dados/respostas/sia_am_200902.html"
    html.parent.mkdir(parents=True)
    html.write_bytes(b"<html>teste</html>")

    for nome in (
        "normalizado.csv",
        "qualidade.json",
        "validacao_cruzada.json",
        "oficial.csv",
    ):
        (pasta / nome).write_bytes(b"conteudo de teste")


def test_gera_manifesto_com_cinco_arquivos(tmp_path):
    preparar_arquivos(tmp_path)

    destino = gerar_manifesto_competencia(
        tmp_path, "SIA", "AM", "2009-02"
    )

    dados = json.loads(destino.read_text(encoding="utf-8"))

    assert dados["competencia"] == "2009-02"
    assert len(dados["arquivos"]) == 5
    assert all(
        len(item["sha256"]) == 64
        for item in dados["arquivos"]
    )


def test_nao_sobrescreve_manifesto(tmp_path):
    preparar_arquivos(tmp_path)

    gerar_manifesto_competencia(
        tmp_path, "SIA", "AM", "2009-02"
    )

    with pytest.raises(FileExistsError):
        gerar_manifesto_competencia(
            tmp_path, "SIA", "AM", "2009-02"
        )


def test_bloqueia_arquivos_incompletos(tmp_path):
    with pytest.raises(FileNotFoundError):
        gerar_manifesto_competencia(
            tmp_path, "SIA", "AM", "2009-02"
        )

    assert not (
        tmp_path
        / "dados/auditoria/sia_am_200902_manifesto.json"
    ).exists()


def test_intervalo_gera_manifesto_automaticamente(
    tmp_path, monkeypatch
):
    chamadas = []

    monkeypatch.setattr(intervalo, "RAIZ", tmp_path)
    monkeypatch.setattr(
        intervalo,
        "listar_competencias",
        lambda inicio, fim: ["2009-02"],
    )
    monkeypatch.setattr(
        intervalo,
        "verificar_competencia",
        lambda competencia: False,
    )
    monkeypatch.setattr(
        intervalo,
        "processar",
        lambda competencia, modo: chamadas.append(
            ("processar", competencia)
        ),
    )
    monkeypatch.setattr(
        intervalo,
        "gerar_manifesto_competencia",
        lambda raiz, sistema, subsistema, competencia:
            chamadas.append(("auditar", competencia))
            or tmp_path / "manifesto.json",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "executar_intervalo.py",
            "--inicio", "2009-02",
            "--fim", "2009-02",
            "--modo", "dinamico",
            "--executar",
        ],
    )

    intervalo.main()

    assert chamadas == [
        ("processar", "2009-02"),
        ("auditar", "2009-02"),
    ]
