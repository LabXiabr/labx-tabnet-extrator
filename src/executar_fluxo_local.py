import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

from core.selecionar_fonte import selecionar_fonte
from core.caminhos import nome_execucao


def executar(script, argumentos):
    comando = [
        sys.executable,
        str(RAIZ / script),
        *argumentos,
    ]
    subprocess.run(comando, cwd=RAIZ, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Fluxo local de validacao SIA/AM"
    )
    parser.add_argument(
        "--competencia", required=True,
        help="Formato AAAA-MM"
    )
    parser.add_argument(
        "--baixar-oficial",
        action="store_true",
        help="Baixa o CSV publico se ainda nao existir",
    )
    parser.add_argument("--sistema", default="SIA")
    parser.add_argument("--subsistema", default="AM")

    args = parser.parse_args()

    if (
        args.sistema.upper() != "SIA"
        or args.subsistema.upper() != "AM"
    ):
        parser.error(
            "Processamento local ainda suporta somente SIA/AM"
        )

    fonte = selecionar_fonte(
        args.sistema, args.subsistema
    )
    grupo = str(fonte["grupo_procedimento"])

    competencia = args.competencia

    try:
        ano, mes = competencia.split("-")
        assert len(ano) == 4 and len(mes) == 2
        assert 1 <= int(mes) <= 12
    except (ValueError, AssertionError):
        parser.error("Competencia invalida. Use AAAA-MM.")

    identificador = ano + mes
    prefixo = nome_execucao(
        args.sistema,
        args.subsistema,
        competencia,
    )

    html = (
        RAIZ / "dados/respostas" / f"{prefixo}.html"
    )
    oficial = (
        RAIZ / "dados/referencias_publicas"
        / f"{prefixo}_oficial.csv"
    )
    pasta_saida = RAIZ / "dados/execucoes" / prefixo

    if pasta_saida.exists():
        raise SystemExit(
            f"Execucao ja existe: {pasta_saida}"
        )

    if not html.is_file():
        raise SystemExit(f"HTML nao encontrado: {html}")


    if not oficial.is_file() and not args.baixar_oficial:
        raise SystemExit(
            "CSV oficial nao encontrado. "
            "Use --baixar-oficial para autorizar o download."
        )


    pasta_saida.parent.mkdir(
        parents=True, exist_ok=True
    )

    with tempfile.TemporaryDirectory(
        dir=pasta_saida.parent,
        prefix=".processando_"
    ) as temporaria:
        temporaria = Path(temporaria)

        csv_saida = temporaria / "normalizado.csv"
        qualidade = temporaria / "qualidade.json"
        cruzada = temporaria / "validacao_cruzada.json"

        referencia = oficial

        if not oficial.is_file():
            referencia = temporaria / "oficial.csv"

            executar(
                "src/core/baixar_csv_publico.py",
                [
                    "--html", str(html),
                    "--saida", str(referencia),
                ],
            )

        executar(
            "src/processamento/normalizar_tabnet.py",
            [
                "--entrada", str(html),
                "--saida", str(csv_saida),
                "--competencia", competencia,
                "--grupo", grupo,
            ],
        )

        executar(
            "src/processamento/relatorio_qualidade.py",
            [
                "--entrada", str(html),
                "--saida", str(qualidade),
                "--competencia", competencia,
                "--grupo", grupo,
            ],
        )

        executar(
            "src/validacao/validar_csv_oficial.py",
            [
                "--oficial", str(referencia),
                "--extraido", str(csv_saida),
                "--competencia", competencia,
                "--saida", str(cruzada),
            ],
        )

        resultado = json.loads(
            cruzada.read_text(encoding="utf-8")
        )

        if resultado["status"] != "aprovado":
            raise SystemExit(
                "Validacao cruzada nao aprovada."
            )

        # Preserva o CSV oficial junto aos resultados.
        destino_oficial = temporaria / "oficial.csv"

        if referencia != destino_oficial:
            shutil.copy2(referencia, destino_oficial)

        if not destino_oficial.is_file():
            raise SystemExit(
                "CSV oficial nao foi preservado."
            )

        # Publica os arquivos somente apos validacao.
        temporaria.rename(pasta_saida)

    print("\n=== FLUXO CONCLUIDO ===")
    print("Competencia:", competencia)
    print("Status:", resultado["status"])
    print("Pasta:", pasta_saida)
    print("Arquivos: normalizado.csv, qualidade.json,")
    print("          validacao_cruzada.json")


if __name__ == "__main__":
    main()
