import json
import os
import re
import subprocess
import sys
from pathlib import Path


def consultar(endpoint):
    resultado = subprocess.run(
        ["gh", "api", "-X", "GET", endpoint],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(resultado.stdout)


def main():
    inicio, fim = sys.argv[1:3]
    repositorio = os.environ["GITHUB_REPOSITORY"]
    execucao_atual = str(os.environ["GITHUB_RUN_ID"])

    endpoint = (
        f"repos/{repositorio}/actions/artifacts"
        "?per_page=100"
    )
    resposta = consultar(endpoint)

    padrao = re.compile(
        r"^resultado-sia-am-"
        r"(\d{4}-\d{2})-a-(\d{4}-\d{2})-\d+$"
    )

    candidatos = []

    for artefato in resposta.get("artifacts", []):
        if artefato.get("expired"):
            continue

        correspondencia = padrao.fullmatch(
            artefato.get("name", "")
        )
        if not correspondencia:
            continue

        primeiro, ultimo = correspondencia.groups()
        if not (primeiro <= inicio and ultimo >= fim):
            continue

        execucao = artefato.get("workflow_run") or {}

        if execucao.get("head_branch") != "main":
            continue

        identificador = str(execucao.get("id", ""))

        if not identificador or identificador == execucao_atual:
            continue

        candidatos.append(artefato)

    candidatos.sort(
        key=lambda a: a["created_at"],
        reverse=True,
    )

    encontrado = None

    for artefato in candidatos:
        identificador = artefato["workflow_run"]["id"]

        execucao = consultar(
            f"repos/{repositorio}/actions/runs/{identificador}"
        )

        if execucao.get("conclusion") == "success":
            encontrado = identificador
            break

    saida = Path(os.environ["GITHUB_OUTPUT"])

    with saida.open("a", encoding="utf-8") as arquivo:
        arquivo.write(
            f"encontrado={'true' if encontrado else 'false'}\n"
        )
        if encontrado:
            arquivo.write(f"run_id={encontrado}\n")

    if encontrado:
        print("Referencia anterior localizada automaticamente.")
    else:
        print("Nenhum pacote anterior compativel encontrado.")
        print("A consulta sera feita sem comparacao historica.")


if __name__ == "__main__":
    main()
