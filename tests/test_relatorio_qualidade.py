import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "processamento"))

from relatorio_qualidade import construir_relatorio


def carregar_html(mes):
    arquivo = RAIZ / "dados" / "respostas" / f"sia_am_{mes}.html"
    return arquivo.read_bytes().decode("iso-8859-1")


def test_relatorio_janeiro():
    relatorio = construir_relatorio(
        carregar_html("200801"), "2008-01", "6"
    )

    assert relatorio["ufs_presentes"] == 27
    assert relatorio["ufs_ausentes"] == []
    assert relatorio["total_informado"] == 36088068
    assert relatorio["total_consistente"] is True
    assert relatorio["status"] == "validado"


def test_relatorio_fevereiro():
    relatorio = construir_relatorio(
        carregar_html("200802"), "2008-02", "6"
    )

    assert relatorio["ufs_presentes"] == 24
    assert relatorio["ufs_ausentes"] == ["MA", "MT", "SE"]
    assert relatorio["total_informado"] == 39128252
    assert relatorio["total_calculado"] == 39128252
    assert relatorio["status"] == "validado_com_ausencias"


def test_relatorio_rejeita_competencia_incorreta():
    with pytest.raises(ValueError):
        construir_relatorio(
            carregar_html("200801"), "2008-02", "6"
        )
