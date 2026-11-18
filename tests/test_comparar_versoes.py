import csv
import importlib.util
from pathlib import Path

import pytest

ARQUIVO = Path(__file__).resolve().parents[1] / "scripts" / "comparar_versoes.py"
ESPEC = importlib.util.spec_from_file_location("comparar_versoes", ARQUIVO)
MODULO = importlib.util.module_from_spec(ESPEC)
ESPEC.loader.exec_module(MODULO)


def salvar(arquivo, linhas):
    with arquivo.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["dt_competencia", "sg_uf", "qt_aprovada"])
        escritor.writerows(linhas)


def test_compara_alteracoes_e_ausencias(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    salvar(a, [["2009-04-01", "GO", 10], ["2009-04-01", "DF", 20]])
    salvar(b, [["2009-04-01", "GO", 15], ["2009-04-01", "AC", 7]])
    rel = MODULO.executar(a, b, tmp_path / "saida")
    assert rel["contagens"] == {"inalterado": 0, "alterado": 1, "incluido": 1, "ausente_na_nova_versao": 1}
    assert rel["diferenca_total"] == -8
    assert (tmp_path / "saida/comparacao.csv").is_file()
    with pytest.raises(FileExistsError):
        MODULO.executar(a, b, tmp_path / "saida")


def test_duplicidade_e_rejeitada(tmp_path):
    a = tmp_path / "a.csv"
    salvar(a, [["2009-04-01", "GO", 10], ["2009-04-01", "GO", 20]])
    with pytest.raises(ValueError, match="Duplicidade"):
        MODULO.carregar(a)


def test_sem_alteracoes(tmp_path):
    a = tmp_path / "a.csv"
    salvar(a, [["2009-04-01", "GO", 10]])
    rel = MODULO.executar(a, a, tmp_path / "saida")
    assert not rel["alteracoes_detectadas"]
    assert rel["contagens"]["inalterado"] == 1
