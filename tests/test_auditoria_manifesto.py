import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src" / "auditoria"))

import verificar_manifesto


def preparar(tmp_path, monkeypatch):
    monkeypatch.setattr(verificar_manifesto, "RAIZ", tmp_path)

    arquivo = tmp_path / "dados" / "teste.csv"
    arquivo.parent.mkdir(parents=True)
    arquivo.write_text("uf,valor\nGO,100\n", encoding="utf-8")

    conteudo = arquivo.read_bytes()

    manifesto = {
        "quantidade_arquivos": 1,
        "arquivos": [
            {
                "arquivo": "dados/teste.csv",
                "tamanho_bytes": len(conteudo),
                "sha256": hashlib.sha256(conteudo).hexdigest(),
            }
        ],
    }

    caminho = tmp_path / "manifesto.json"
    caminho.write_text(
        json.dumps(manifesto),
        encoding="utf-8",
    )

    return arquivo, caminho


def test_arquivo_integro(tmp_path, monkeypatch):
    _, manifesto = preparar(tmp_path, monkeypatch)

    assert verificar_manifesto.verificar(manifesto) is True


def test_detecta_arquivo_alterado(tmp_path, monkeypatch):
    arquivo, manifesto = preparar(tmp_path, monkeypatch)

    arquivo.write_text(
        "uf,valor\nGO,101\n",
        encoding="utf-8",
    )

    assert verificar_manifesto.verificar(manifesto) is False


def test_detecta_arquivo_ausente(tmp_path, monkeypatch):
    arquivo, manifesto = preparar(tmp_path, monkeypatch)

    arquivo.unlink()

    assert verificar_manifesto.verificar(manifesto) is False
