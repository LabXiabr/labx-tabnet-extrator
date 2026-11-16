import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "dados/auditoria/sia_am_2008_manifesto.json"


def sha256(arquivo):
    digest = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def registrar(caminho):
    if not caminho.is_file():
        raise FileNotFoundError(caminho)

    return {
        "arquivo": str(caminho.relative_to(RAIZ)),
        "tamanho_bytes": caminho.stat().st_size,
        "sha256": sha256(caminho),
    }


def main():
    arquivos = []

    for mes in range(1, 13):
        pasta = (
            RAIZ / "dados/execucoes"
            / f"sia_am_2008{mes:02d}"
        )

        for nome in (
            "normalizado.csv",
            "qualidade.json",
            "validacao_cruzada.json",
        ):
            arquivos.append(registrar(pasta / nome))

    pasta = RAIZ / "dados/consolidados"

    for nome in (
        "sia_am_200801_200812.csv",
        "sia_am_200801_200812_qualidade.json",
    ):
        arquivos.append(registrar(pasta / nome))

    manifesto = {
        "projeto": "LABX TabNet Extrator",
        "sistema": "SIA",
        "subsistema": "AM",
        "periodo": "2008-01 a 2008-12",
        "gerado_em_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "quantidade_arquivos": len(arquivos),
        "arquivos": arquivos,
    }

    DESTINO.parent.mkdir(parents=True, exist_ok=True)

    with DESTINO.open("x", encoding="utf-8") as f:
        json.dump(
            manifesto, f,
            ensure_ascii=False, indent=2
        )
        f.write("\n")

    print("=== MANIFESTO GERADO ===")
    print("Arquivos registrados:", len(arquivos))
    print("Destino:", DESTINO)
    print("Nenhum arquivo de dados foi modificado.")


if __name__ == "__main__":
    main()
