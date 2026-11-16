import argparse
import subprocess
import sys
import time
from pathlib import Path

from core.gerar_consultas import listar_competencias
from core.caminhos import nome_execucao
from auditoria.manifesto_competencia import gerar_manifesto_competencia
from auditoria.verificar_manifesto_competencia import verificar_manifesto_competencia
from executar_intervalo_planejador import verificar_competencia

RAIZ = Path(__file__).resolve().parents[1]


def executar(script, argumentos):
    comando = [
        sys.executable,
        str(RAIZ / script),
        *argumentos,
    ]
    subprocess.run(
        comando,
        cwd=RAIZ,
        check=True,
    )


def processar(competencia, modo="legado"):
    prefixo = nome_execucao(
        "SIA", "AM", competencia
    )

    consulta = RAIZ / "dados/consultas" / f"{prefixo}.json"
    html = RAIZ / "dados/respostas" / f"{prefixo}.html"
    pasta = RAIZ / "dados/execucoes" / prefixo

    if modo == "legado" and not consulta.is_file():
        raise RuntimeError(
            f"{competencia}: configuracao nao encontrada"
        )

    if pasta.exists():
        raise RuntimeError(
            f"{competencia}: pasta de execucao ja existe, "
            "mas nao esta aprovada. Verifique antes de continuar."
        )

    if not html.is_file():
        print(
            f"\n=== CONSULTANDO {competencia} ===",
            flush=True,
        )

        if modo == "dinamico":
            argumentos = [
                "--sistema", "SIA",
                "--subsistema", "AM",
                "--competencia", competencia,
                "--saida", str(html),
            ]
        else:
            argumentos = [
                "--consulta", str(consulta),
                "--saida", str(html),
            ]

        executar(
            "src/core/executar_consulta.py",
            argumentos,
        )
    else:
        print(
            f"{competencia}: reutilizando HTML existente",
            flush=True,
        )

    print(
        f"\n=== VALIDANDO {competencia} ===",
        flush=True,
    )

    executar(
        "src/executar_fluxo_local.py",
        [
            "--competencia", competencia,
            "--baixar-oficial",
        ],
    )

    if not verificar_competencia(competencia):
        raise RuntimeError(
            f"{competencia}: validacao final nao aprovada"
        )

    print(f"{competencia}: APROVADA", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Executor de intervalos SIA/AM"
    )
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)

    parser.add_argument(
        "--modo",
        choices=("legado", "dinamico"),
        default="legado",
        help="Forma de preparar as consultas",
    )
    parser.add_argument("--sistema", default="SIA")
    parser.add_argument("--subsistema", default="AM")

    parser.add_argument(
        "--executar",
        action="store_true",
        help="Autoriza consultas publicas e processamento",
    )
    parser.add_argument(
        "--consolidar",
        action="store_true",
        help="Gera um CSV unico apos validar o intervalo",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=2,
        help="Maximo de competencias pendentes por execucao",
    )

    parser.add_argument(
        "--manifesto",
        help="Verifica a integridade antes de processar",
    )

    args = parser.parse_args()

    if (
        args.sistema.upper() != "SIA"
        or args.subsistema.upper() != "AM"
    ):
        parser.error(
            "Este executor ainda suporta somente SIA/AM"
        )

    if args.manifesto:
        print(
            "\n=== AUDITORIA PRELIMINAR ===",
            flush=True,
        )

        executar(
            "src/auditoria/verificar_manifesto.py",
            [
                "--manifesto",
                str(Path(args.manifesto).resolve()),
            ],
        )

    if args.limite < 1:
        parser.error("--limite deve ser maior que zero")

    competencias = listar_competencias(
        args.inicio, args.fim
    )

    pendentes = [
        c for c in competencias
        if not verificar_competencia(c)
    ]

    # Verifica a auditoria antes de reutilizar competencias.
    aprovadas = [
        c for c in competencias if c not in pendentes
    ]

    manifesto_historico = (
        args.manifesto is not None
        and Path(args.manifesto).name
        == "sia_am_2008_manifesto.json"
    )

    for competencia in aprovadas:
        prefixo = nome_execucao(
            "SIA", "AM", competencia
        )

        mensal = (
            RAIZ / "dados/auditoria"
            / f"{prefixo}_manifesto.json"
        )

        if mensal.is_file():
            problemas = verificar_manifesto_competencia(
                RAIZ, "SIA", "AM", competencia
            )

            if problemas:
                raise SystemExit(
                    f"{competencia}: auditoria reprovada: "
                    + "; ".join(problemas)
                )

            continue

        # Os arquivos de 2008 possuem um manifesto anual.
        if (
            competencia.startswith("2008-")
            and manifesto_historico
        ):
            continue

        aviso = (
            f"{competencia}: competencia aprovada, "
            "mas sem manifesto mensal verificado"
        )

        if args.executar:
            raise SystemExit(
                aviso + ". Execucao bloqueada."
            )

        print("AVISO:", aviso, flush=True)

    print("\n=== PLANEJAMENTO ===", flush=True)
    print("Inicio:", args.inicio)
    print("Fim:", args.fim)
    print("Total:", len(competencias))
    print("Aprovadas:", len(competencias) - len(pendentes))
    print("Pendentes:", len(pendentes))

    for c in competencias:
        status = (
            "APROVADA"
            if c not in pendentes
            else "PENDENTE"
        )
        print(f"{c}: {status}")

    if not args.executar:
        print("\nSimulacao: nenhuma consulta enviada.")
        return

    if len(pendentes) > args.limite:
        raise SystemExit(
            f"\nExistem {len(pendentes)} competencias pendentes, "
            f"acima do limite {args.limite}. "
            "Reduza o intervalo ou ajuste --limite."
        )

    if pendentes and args.modo == "legado":
        executar(
            "src/core/gerar_consultas.py",
            [
                "--inicio", args.inicio,
                "--fim", args.fim,
                "--gravar",
            ],
        )

    for indice, competencia in enumerate(pendentes):
        if indice:
            time.sleep(2)

        processar(competencia, modo=args.modo)

        manifesto_competencia = gerar_manifesto_competencia(
            RAIZ,
            "SIA",
            "AM",
            competencia,
        )
        print(
            f"{competencia}: manifesto criado: "
            f"{manifesto_competencia}",
            flush=True,
        )

    print("\n=== INTERVALO VALIDADO ===", flush=True)

    if args.consolidar:
        if not all(
            verificar_competencia(c)
            for c in competencias
        ):
            raise SystemExit(
                "Consolidacao bloqueada: competencia pendente."
            )

        identificador = (
            f"sia_am_{args.inicio.replace('-', '')}_"
            f"{args.fim.replace('-', '')}"
        )

        pasta = RAIZ / "dados/consolidados"
        csv_final = pasta / f"{identificador}.csv"
        json_final = pasta / f"{identificador}_qualidade.json"

        if csv_final.exists() or json_final.exists():
            if not (csv_final.is_file() and json_final.is_file()):
                raise SystemExit(
                    "Consolidado incompleto: verifique os arquivos."
                )

            print(
                "Consolidado existente preservado:",
                csv_final,
            )
            return

        executar(
            "src/consolidacao/consolidar_periodo.py",
            [
                "--inicio", args.inicio,
                "--fim", args.fim,
            ],
        )

        print(
            "\nConsolidacao finalizada.",
            flush=True,
        )


if __name__ == "__main__":
    main()
