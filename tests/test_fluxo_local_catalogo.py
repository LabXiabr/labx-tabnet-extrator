import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import executar_fluxo_local as fluxo


def configurar(tmp_path, monkeypatch, argumentos):
    monkeypatch.setattr(fluxo, "RAIZ", tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["executar_fluxo_local.py", *argumentos],
    )
    monkeypatch.setattr(
        fluxo,
        "selecionar_fonte",
        lambda sistema, subsistema: {
            "grupo_procedimento": "6"
        },
    )


def test_bloqueia_execucao_existente(tmp_path, monkeypatch):
    configurar(
        tmp_path, monkeypatch,
        ["--competencia", "2008-03"],
    )

    pasta = tmp_path / "dados/execucoes/sia_am_200803"
    pasta.mkdir(parents=True)

    with pytest.raises(
        SystemExit, match="Execucao ja existe"
    ):
        fluxo.main()


def test_rejeita_subsistema_nao_suportado(
    tmp_path, monkeypatch
):
    configurar(
        tmp_path, monkeypatch,
        [
            "--competencia", "2008-03",
            "--sistema", "SIH",
            "--subsistema", "RD",
        ],
    )

    with pytest.raises(SystemExit) as erro:
        fluxo.main()

    assert erro.value.code == 2


def test_utiliza_grupo_do_catalogo(tmp_path, monkeypatch):
    configurar(
        tmp_path, monkeypatch,
        [
            "--competencia", "2008-03",
            "--baixar-oficial",
        ],
    )

    html = tmp_path / "dados/respostas/sia_am_200803.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html></html>", encoding="utf-8")

    chamadas = []

    def executar_simulado(script, argumentos):
        chamadas.append((script, argumentos))

        if script == "src/core/baixar_csv_publico.py":
            destino = Path(argumentos[argumentos.index("--saida") + 1])
            destino.write_text("teste", encoding="utf-8")

        elif script == "src/processamento/normalizar_tabnet.py":
            destino = Path(argumentos[argumentos.index("--saida") + 1])
            destino.write_text("sg_uf,dt_competencia,qt_aprovada\nGO,2008-03,1\n")

        elif script == "src/processamento/relatorio_qualidade.py":
            destino = Path(argumentos[argumentos.index("--saida") + 1])
            destino.write_text("{}", encoding="utf-8")

        elif script == "src/validacao/validar_csv_oficial.py":
            destino = Path(argumentos[argumentos.index("--saida") + 1])
            destino.write_text(
                json.dumps({"status": "aprovado"}),
                encoding="utf-8",
            )

    monkeypatch.setattr(
        fluxo, "executar", executar_simulado
    )

    fluxo.main()

    for script, argumentos in chamadas:
        if script in (
            "src/processamento/normalizar_tabnet.py",
            "src/processamento/relatorio_qualidade.py",
        ):
            indice = argumentos.index("--grupo")
            assert argumentos[indice + 1] == "6"

    assert (
        tmp_path / "dados/execucoes/sia_am_200803"
        / "validacao_cruzada.json"
    ).is_file()
