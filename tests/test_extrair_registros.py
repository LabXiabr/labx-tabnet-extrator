import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src" / "processamento")
)

from normalizar_tabnet import extrair_registros


BASE = Path("tests/fixtures/dados/respostas")


def carregar_html(mes):
    return (BASE / f"sia_am_{mes}.html").read_bytes().decode(
        "iso-8859-1",
        errors="replace"
    )


def test_janeiro_2008():
    registros, total = extrair_registros(
        carregar_html("200801"),
        "2008-01",
        "6"
    )

    assert len(registros) == 27
    assert total == 36088068
    assert registros[0]["sg_uf"] == "RO"
    assert registros[0]["qt_aprovada"] == 35943


def test_fevereiro_2008():
    registros, total = extrair_registros(
        carregar_html("200802"),
        "2008-02",
        "6"
    )

    ufs = {r["sg_uf"] for r in registros}

    assert len(registros) == 24
    assert total == 39128252
    assert {"MA", "MT", "SE"}.isdisjoint(ufs)
    assert sum(r["qt_aprovada"] for r in registros) == total


def test_competencia_incorreta():
    with pytest.raises(ValueError):
        extrair_registros(
            carregar_html("200801"),
            "2008-02",
            "6"
        )


def test_grupo_incorreto():
    with pytest.raises(ValueError):
        extrair_registros(
            carregar_html("200801"),
            "2008-01",
            "3"
        )


def test_total_adulterado():
    html = carregar_html("200801")

    html = html.replace(
        "<TD>36.088.068",
        "<TD>36.088.069"
    )

    assert html != carregar_html("200801")

    with pytest.raises(ValueError, match="Total divergente"):
        extrair_registros(html, "2008-01", "6")
