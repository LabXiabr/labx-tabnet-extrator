import json
from pathlib import Path

import pytest

from src.catalogo.fontes import carregar_fonte, listar_fontes, obter_fonte
from scripts.gerar_proveniencia import gerar


def test_catalogo_tem_uma_fonte_homologada_e_outra_planejada():
    fontes = listar_fontes()
    assert {f.id for f in fontes} >= {"sia_am", "sia_pa"}
    assert obter_fonte("SIA", "AM").homologada
    with pytest.raises(ValueError, match="nao homologada"):
        obter_fonte("SIA", "PA")


def test_proveniencia_nao_sobrescreve_saida(tmp_path):
    csv = tmp_path / "normalizado.csv"
    csv.write_text("sg_uf,dt_competencia,qt_aprovada\nGO,2009-04-01,2\n", encoding="utf-8")
    saida = tmp_path / "proveniencia.json"
    fonte = obter_fonte("SIA", "AM")
    gerado = gerar(fonte, "2009-04", csv, saida, commit="abc123")
    assert len(gerado["csv_sha256"]) == 64
    assert json.loads(saida.read_text(encoding="utf-8"))["git_commit"] == "abc123"
    with pytest.raises(FileExistsError):
        gerar(fonte, "2009-04", csv, saida)


def test_catalogo_rejeita_fonte_nao_verificada_com_status_homologada(tmp_path):
    fonte = obter_fonte("SIA", "AM").to_dict()
    fonte["url_formulario"] = None
    arquivo = tmp_path / "invalido.json"
    arquivo.write_text(json.dumps(fonte), encoding="utf-8")
    with pytest.raises(ValueError, match="homologada requer URL"):
        carregar_fonte(arquivo)


def test_rejeita_url_externa(tmp_path):
    fonte = obter_fonte("SIA", "AM").to_dict()
    fonte["url_formulario"] = "https://example.com/"
    arquivo = tmp_path / "invalido.json"
    arquivo.write_text(json.dumps(fonte), encoding="utf-8")
    with pytest.raises(ValueError, match="URL deve"):
        carregar_fonte(arquivo)
