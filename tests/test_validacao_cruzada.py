import csv
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "validacao"))

from validar_csv_oficial import (
    carregar_oficial,
    carregar_extraido,
)

OFICIAL = (
    RAIZ
    / "tests/fixtures/dados/referencias_publicas/sia_am_200802_oficial.csv"
)

EXTRAIDO = RAIZ / "tests/fixtures/dados/saida/sia_am_200802.csv"


def test_csv_oficial_fevereiro():
    valores, total = carregar_oficial(OFICIAL, "2008-02")

    assert len(valores) == 24
    assert total == 39128252
    assert valores["RO"] == 80480
    assert {"MA", "MT", "SE"}.isdisjoint(valores)


def test_csv_extraido_equivalente_ao_oficial():
    oficial, total = carregar_oficial(OFICIAL, "2008-02")
    extraido = carregar_extraido(EXTRAIDO, "2008-02")

    assert extraido == oficial
    assert sum(extraido.values()) == total


def test_detecta_valor_alterado(tmp_path):
    with EXTRAIDO.open(
        encoding="utf-8", newline=""
    ) as arquivo:
        leitor = csv.DictReader(arquivo)
        campos = leitor.fieldnames
        registros = list(leitor)

    for registro in registros:
        if registro["sg_uf"] == "RO":
            registro["qt_aprovada"] = "80481"

    alterado = tmp_path / "alterado.csv"

    with alterado.open(
        "w", encoding="utf-8", newline=""
    ) as arquivo:
        escritor = csv.DictWriter(
            arquivo, fieldnames=campos
        )
        escritor.writeheader()
        escritor.writerows(registros)

    oficial, _ = carregar_oficial(OFICIAL, "2008-02")
    extraido = carregar_extraido(alterado, "2008-02")

    divergencias = {
        uf: (oficial.get(uf), extraido.get(uf))
        for uf in set(oficial) | set(extraido)
        if oficial.get(uf) != extraido.get(uf)
    }

    assert divergencias == {
        "RO": (80480, 80481)
    }


def test_rejeita_competencia_incorreta():
    with pytest.raises(ValueError):
        carregar_oficial(OFICIAL, "2008-03")
