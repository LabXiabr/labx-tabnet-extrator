import json
import sys
from pathlib import Path

import pytest

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_PROJETO / "src"))

import executar_fluxo_local as fluxo


@pytest.mark.parametrize("oficial_existente", [True, False])
def test_preserva_csv_oficial(
    tmp_path, monkeypatch, oficial_existente
):
    monkeypatch.setattr(fluxo, "RAIZ", tmp_path)
    monkeypatch.setattr(
        fluxo,
        "selecionar_fonte",
        lambda sistema, subsistema: {
            "grupo_procedimento": "6"
        },
    )

    argumentos = [
        "executar_fluxo_local.py",
        "--competencia", "2008-03",
    ]

    if not oficial_existente:
        argumentos.append("--baixar-oficial")

    monkeypatch.setattr(sys, "argv", argumentos)

    html = (
        tmp_path
        / "dados/respostas/sia_am_200803.html"
    )
    html.parent.mkdir(parents=True)
    html.write_text("<html></html>", encoding="utf-8")

    referencia = (
        tmp_path
        / "dados/referencias_publicas"
        / "sia_am_200803_oficial.csv"
    )

    conteudo_oficial = b"CSV OFICIAL DE TESTE\n"

    if oficial_existente:
        referencia.parent.mkdir(parents=True)
        referencia.write_bytes(conteudo_oficial)

    def executar_simulado(script, argumentos):
        saida = Path(
            argumentos[argumentos.index("--saida") + 1]
        )

        saida.parent.mkdir(parents=True, exist_ok=True)

        if script == "src/core/baixar_csv_publico.py":
            saida.write_bytes(conteudo_oficial)

        elif script == "src/processamento/normalizar_tabnet.py":
            saida.write_text(
                "sg_uf,dt_competencia,qt_aprovada\n"
                "GO,2008-03-01,10\n",
                encoding="utf-8",
            )

        elif script == "src/processamento/relatorio_qualidade.py":
            saida.write_text(
                json.dumps({"status": "validado"}),
                encoding="utf-8",
            )

        elif script == "src/validacao/validar_csv_oficial.py":
            saida.write_text(
                json.dumps({"status": "aprovado"}),
                encoding="utf-8",
            )

    monkeypatch.setattr(
        fluxo, "executar", executar_simulado
    )

    fluxo.main()

    pasta = (
        tmp_path
        / "dados/execucoes/sia_am_200803"
    )

    for nome in (
        "normalizado.csv",
        "qualidade.json",
        "validacao_cruzada.json",
        "oficial.csv",
    ):
        assert (pasta / nome).is_file()

    assert (
        pasta / "oficial.csv"
    ).read_bytes() == conteudo_oficial

    if oficial_existente:
        assert referencia.read_bytes() == conteudo_oficial
