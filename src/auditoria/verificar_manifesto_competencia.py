import argparse
import hashlib
import json
from pathlib import Path

from core.caminhos import nome_execucao


def verificar_manifesto_competencia(
    raiz, sistema, subsistema, competencia
):
    raiz = Path(raiz).resolve()

    prefixo = nome_execucao(
        sistema, subsistema, competencia
    )

    manifesto = (
        raiz / "dados/auditoria"
        / f"{prefixo}_manifesto.json"
    )

    if not manifesto.is_file():
        return [f"Manifesto ausente: {manifesto}"]

    try:
        dados = json.loads(
            manifesto.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, UnicodeError) as erro:
        return [f"Manifesto invalido: {erro}"]

    if not isinstance(dados, dict):
        return ["Estrutura do manifesto invalida"]

    esperados = [
        f"dados/respostas/{prefixo}.html",
        f"dados/execucoes/{prefixo}/normalizado.csv",
        f"dados/execucoes/{prefixo}/qualidade.json",
        f"dados/execucoes/{prefixo}/validacao_cruzada.json",
        f"dados/execucoes/{prefixo}/oficial.csv",
    ]

    registros = dados.get("arquivos")

    if (
        dados.get("versao") != 1
        or dados.get("sistema") != sistema.upper()
        or dados.get("subsistema") != subsistema.upper()
        or dados.get("competencia") != competencia
        or dados.get("total_arquivos") != 5
        or not isinstance(registros, list)
        or len(registros) != 5
    ):
        return ["Metadados do manifesto inconsistentes"]

    problemas = []
    caminhos = []

    for item in registros:
        if not isinstance(item, dict):
            return ["Registro invalido no manifesto"]

        caminhos.append(item.get("caminho"))

    if (
        len(set(str(c) for c in caminhos)) != 5
        or set(caminhos) != set(esperados)
    ):
        return ["Lista de arquivos diferente da esperada"]

    for item in registros:
        relativo = item["caminho"]
        caminho = raiz / relativo

        if not caminho.is_file():
            problemas.append(f"Ausente: {relativo}")
            continue

        conteudo = caminho.read_bytes()
        hash_atual = hashlib.sha256(conteudo).hexdigest()

        if (
            len(conteudo) != item.get("tamanho_bytes")
            or hash_atual != item.get("sha256")
        ):
            problemas.append(f"Alterado: {relativo}")

    return problemas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raiz", default=".")
    parser.add_argument("--sistema", default="SIA")
    parser.add_argument("--subsistema", default="AM")
    parser.add_argument("--competencia", required=True)
    args = parser.parse_args()

    problemas = verificar_manifesto_competencia(
        args.raiz,
        args.sistema,
        args.subsistema,
        args.competencia,
    )

    print("=== VERIFICACAO DE MANIFESTO ===")
    print("Competencia:", args.competencia)
    print("Problemas encontrados:", len(problemas))

    for problema in problemas:
        print(problema)

    if problemas:
        raise SystemExit(1)

    print("Status: APROVADO")


if __name__ == "__main__":
    main()
