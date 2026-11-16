import sys
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO / "src"))

from auditoria.manifesto_competencia import (
    gerar_manifesto_competencia,
)
from auditoria.verificar_manifesto_competencia import (
    verificar_manifesto_competencia,
)


def preparar(tmp_path):
    pasta = tmp_path / "dados/execucoes/sia_am_200902"
    pasta.mkdir(parents=True)

    html = tmp_path / "dados/respostas/sia_am_200902.html"
    html.parent.mkdir(parents=True)
    html.write_bytes(b"<html>teste</html>")

    for nome in (
        "normalizado.csv",
        "qualidade.json",
        "validacao_cruzada.json",
        "oficial.csv",
    ):
        (pasta / nome).write_bytes(b"conteudo teste")

    gerar_manifesto_competencia(
        tmp_path, "SIA", "AM", "2009-02"
    )

    return pasta


def verificar(tmp_path):
    return verificar_manifesto_competencia(
        tmp_path, "SIA", "AM", "2009-02"
    )


def test_manifesto_integro(tmp_path):
    preparar(tmp_path)
    assert verificar(tmp_path) == []


def test_detecta_arquivo_alterado(tmp_path):
    pasta = preparar(tmp_path)
    (pasta / "normalizado.csv").write_bytes(b"alterado")

    problemas = verificar(tmp_path)
    assert any("Alterado:" in p for p in problemas)


def test_detecta_manifesto_ausente(tmp_path):
    problemas = verificar(tmp_path)
    assert any("Manifesto ausente:" in p for p in problemas)
