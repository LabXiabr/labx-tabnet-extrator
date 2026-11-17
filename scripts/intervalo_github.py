import re
import shutil
import subprocess
import sys
import os
from pathlib import Path


def competencias(inicio, fim, limite):
    if not re.fullmatch(r"2009-(0[1-9]|1[0-2])", inicio):
        raise ValueError("Inicio deve ser um mes de 2009")

    if not re.fullmatch(r"2009-(0[1-9]|1[0-2])", fim):
        raise ValueError("Fim deve ser um mes de 2009")

    limite = int(limite)
    if not 1 <= limite <= 3:
        raise ValueError("Limite permitido: 1 a 3")

    a = int(inicio[-2:])
    b = int(fim[-2:])

    if a > b:
        raise ValueError("Inicio posterior ao fim")

    meses = [f"2009-{m:02d}" for m in range(a, b + 1)]

    if len(meses) > limite:
        raise ValueError(
            f"Intervalo com {len(meses)} meses excede "
            f"o limite de {limite}"
        )

    return meses


def empacotar(meses):
    pacote = Path("pacote")

    if pacote.exists():
        raise RuntimeError("Pasta pacote ja existe")

    aprovadas = []

    for competencia in meses:
        mes = competencia.replace("-", "")
        prefixo = f"sia_am_{mes}"

        pasta = Path("dados/execucoes") / prefixo

        arquivos = {
            "normalizado.csv": pasta / "normalizado.csv",
            "oficial.csv": pasta / "oficial.csv",
            "qualidade.json": pasta / "qualidade.json",
            "validacao_cruzada.json": pasta / "validacao_cruzada.json",
            "manifesto.json": (
                Path("dados/auditoria")
                / f"{prefixo}_manifesto.json"
            ),
            "resposta_original.html": (
                Path("dados/respostas") / f"{prefixo}.html"
            ),
        }

        if not all(p.is_file() for p in arquivos.values()):
            print(f"{competencia}: arquivos incompletos")
            continue

        resultado = subprocess.run(
            [
                sys.executable,
                "scripts/resumir_execucao.py",
                competencia,
            ],
            check=False,
        )

        if resultado.returncode != 0:
            print(f"{competencia}: validacao nao aprovada")
            continue

        destino = pacote / prefixo
        destino.mkdir(parents=True, exist_ok=False)

        for nome, origem in arquivos.items():
            shutil.copy2(origem, destino / nome)

        aprovadas.append(competencia)
        print(f"{competencia}: pacote aprovado")

    if len(aprovadas) == len(meses):
        identificador = (
            f"sia_am_{meses[0].replace('-', '')}_"
            f"{meses[-1].replace('-', '')}"
        )

        origem = Path("dados/consolidados")
        consolidados = [
            origem / f"{identificador}.csv",
            origem / f"{identificador}_qualidade.json",
        ]

        if not all(p.is_file() for p in consolidados):
            raise RuntimeError(
                "Intervalo aprovado, mas consolidado ausente."
            )

        shutil.copy2(
            consolidados[0],
            pacote / "consolidado.csv",
        )
        shutil.copy2(
            consolidados[1],
            pacote / "qualidade_consolidado.json",
        )

        print("CSV consolidado incluido no pacote.")

    print(
        f"\nPacotes aprovados: {len(aprovadas)}/{len(meses)}"
    )

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write(
                f"\n## Intervalo: {meses[0]} a {meses[-1]}\n"
                f"\nCompetencias aprovadas: "
                f"**{len(aprovadas)}/{len(meses)}**\n"
            )

    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        with open(saida, "a", encoding="utf-8") as f:
            f.write(
                f"has_files={'true' if aprovadas else 'false'}\n"
            )


    if len(aprovadas) != len(meses):
        raise RuntimeError(
            "Intervalo incompleto: "
            f"{len(aprovadas)}/{len(meses)} "
            "competencias empacotadas."
        )


def main():
    if len(sys.argv) != 5:
        raise SystemExit(
            "Uso: intervalo_github.py "
            "validar|empacotar INICIO FIM LIMITE"
        )

    acao, inicio, fim, limite = sys.argv[1:]

    try:
        meses = competencias(inicio, fim, limite)
    except ValueError as erro:
        raise SystemExit(str(erro))

    print("Competencias:", ", ".join(meses))

    if acao == "validar":
        print("Intervalo permitido. Nenhuma consulta enviada.")
    elif acao == "empacotar":
        empacotar(meses)
    else:
        raise SystemExit("Acao desconhecida")


if __name__ == "__main__":
    main()
