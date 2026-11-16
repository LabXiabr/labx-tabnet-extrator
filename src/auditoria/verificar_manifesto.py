import argparse
import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def calcular_sha256(caminho):
    digest = hashlib.sha256()

    with caminho.open("rb") as arquivo:
        for bloco in iter(
            lambda: arquivo.read(1024 * 1024), b""
        ):
            digest.update(bloco)

    return digest.hexdigest()


def verificar(manifesto_path):
    manifesto = json.loads(
        manifesto_path.read_text(encoding="utf-8")
    )

    arquivos = manifesto["arquivos"]

    if (
        not isinstance(arquivos, list)
        or len(arquivos) != manifesto["quantidade_arquivos"]
        or not arquivos
    ):
        raise ValueError("Manifesto com quantidade invalida")

    problemas = []
    caminhos = set()

    for item in arquivos:
        nome = item["arquivo"]
        caminho = (RAIZ / nome).resolve()

        if (
            caminho == RAIZ
            or not caminho.is_relative_to(RAIZ)
            or nome in caminhos
        ):
            raise ValueError(
                f"Caminho invalido ou duplicado: {nome}"
            )

        caminhos.add(nome)

        if not caminho.is_file():
            problemas.append(f"AUSENTE: {nome}")
            continue

        tamanho = caminho.stat().st_size
        hash_atual = calcular_sha256(caminho)

        if tamanho != item["tamanho_bytes"]:
            problemas.append(f"TAMANHO ALTERADO: {nome}")

        if hash_atual != item["sha256"]:
            problemas.append(f"HASH DIVERGENTE: {nome}")

    print("=== VERIFICACAO DE INTEGRIDADE ===")
    print("Arquivos registrados:", len(arquivos))
    print("Problemas encontrados:", len(problemas))

    if problemas:
        for problema in problemas:
            print(problema)

        print("Status: REPROVADO")
        return False

    print("Status: APROVADO")
    print("Todos os arquivos correspondem ao manifesto.")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifesto", required=True)
    args = parser.parse_args()

    caminho = Path(args.manifesto)

    if not verificar(caminho):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
