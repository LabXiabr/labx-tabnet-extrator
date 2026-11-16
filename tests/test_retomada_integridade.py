import sys
from pathlib import Path

import pytest

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO / "src"))

import executar_intervalo as intervalo
from auditoria.manifesto_competencia import (
    gerar_manifesto_competencia,
)


def preparar(tmp_path):
    prefixo = "sia_am_200902"

    pasta = tmp_path / "dados/execucoes" / prefixo
    pasta.mkdir(parents=True)

    html = tmp_path / "dados/respostas" / f"{prefixo}.html"
    html.parent.mkdir(parents=True)
    html.write_bytes(b"<html>dados de teste</html>")

    for nome in (
        "normalizado.csv",
        "qualidade.json",
        "validacao_cruzada.json",
        "oficial.csv",
    ):
        (pasta / nome).write_bytes(b"conteudo original")

    gerar_manifesto_competencia(
        tmp_path, "SIA", "AM", "2009-02"
    )

    return pasta


def configurar(monkeypatch, tmp_path):
    monkeypatch.setattr(intervalo, "RAIZ", tmp_path)

    monkeypatch.setattr(
        intervalo,
        "listar_competencias",
        lambda inicio, fim: ["2009-02"],
    )

    monkeypatch.setattr(
        intervalo,
        "verificar_competencia",
        lambda competencia: True,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "executar_intervalo.py",
            "--inicio", "2009-02",
            "--fim", "2009-02",
            "--modo", "dinamico",
        ],
    )


def test_retomada_com_manifesto_integro(
    tmp_path, monkeypatch
):
    preparar(tmp_path)
    configurar(monkeypatch, tmp_path)

    intervalo.main()


def test_retomada_bloqueia_arquivo_alterado(
    tmp_path, monkeypatch
):
    pasta = preparar(tmp_path)
    configurar(monkeypatch, tmp_path)

    (pasta / "oficial.csv").write_bytes(
        b"conteudo modificado"
    )

    with pytest.raises(
        SystemExit, match="auditoria reprovada"
    ):
        intervalo.main()
