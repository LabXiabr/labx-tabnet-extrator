import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import executar_intervalo as modulo


def preparar(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo, "RAIZ", tmp_path)

    chamadas = []

    def executar_simulado(script, argumentos):
        chamadas.append((script, argumentos))

    monkeypatch.setattr(
        modulo, "executar", executar_simulado
    )
    monkeypatch.setattr(
        modulo, "verificar_competencia",
        lambda competencia: True,
    )

    return chamadas


def test_modo_dinamico_sem_json(tmp_path, monkeypatch):
    chamadas = preparar(tmp_path, monkeypatch)

    modulo.processar("2008-03", modo="dinamico")

    assert len(chamadas) == 2

    script, argumentos = chamadas[0]

    assert script == "src/core/executar_consulta.py"
    assert "--consulta" not in argumentos

    assert argumentos[:6] == [
        "--sistema", "SIA",
        "--subsistema", "AM",
        "--competencia", "2008-03",
    ]

    assert chamadas[1][0] == (
        "src/executar_fluxo_local.py"
    )


def test_modo_legado_com_json(tmp_path, monkeypatch):
    chamadas = preparar(tmp_path, monkeypatch)

    pasta = tmp_path / "dados/consultas"
    pasta.mkdir(parents=True)

    consulta = pasta / "sia_am_200803.json"
    consulta.write_text("{}", encoding="utf-8")

    modulo.processar("2008-03", modo="legado")

    assert len(chamadas) == 2

    script, argumentos = chamadas[0]

    assert script == "src/core/executar_consulta.py"
    assert "--consulta" in argumentos
    assert str(consulta) in argumentos


def test_bloqueia_execucao_existente_nao_aprovada(
    tmp_path, monkeypatch
):
    import pytest

    preparar(tmp_path, monkeypatch)

    pasta = (
        tmp_path
        / "dados/execucoes/sia_am_200803"
    )
    pasta.mkdir(parents=True)

    with pytest.raises(
        RuntimeError,
        match="nao esta aprovada"
    ):
        modulo.processar(
            "2008-03",
            modo="dinamico",
        )
