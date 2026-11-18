import os
from pathlib import Path
import pytest

from scripts.preservar_referencia import preservar


def test_fora_do_github_nao_move(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(RuntimeError, match='GitHub Actions'):
        preservar('2009-04', '2009-04', tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_preserva_sem_sobrescrever(tmp_path, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    nome='sia_am_200904'
    ex=tmp_path/'dados/execucoes'/nome
    ex.mkdir(parents=True)
    (ex/'normalizado.csv').write_text('a,b\n')
    html=tmp_path/'dados/respostas'/f'{nome}.html'
    html.parent.mkdir(parents=True)
    html.write_text('pagina')
    man=tmp_path/'dados/auditoria'/f'{nome}_manifesto.json'
    man.parent.mkdir(parents=True)
    man.write_text('{}')
    preservar('2009-04','2009-04',tmp_path)
    assert (tmp_path/'anteriores'/nome/'execucao/normalizado.csv').is_file()
    assert not ex.exists() and not html.exists() and not man.exists()
    with pytest.raises(RuntimeError):
        preservar('2009-04','2009-04',tmp_path)
