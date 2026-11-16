import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def executar_dados(dados, saida, simular=False):
    if dados.get("metodo", "").upper() != "POST":
        sys.exit("Erro: metodo diferente de POST.")

    parametros = [tuple(p) for p in dados["parametros"]]

    valores = {}
    for nome, valor in parametros:
        valores.setdefault(nome, []).append(valor)

    esperados = {
        "Linha": "Ano/mês_processamento",
        "Coluna": "UF",
        "Incremento": "Qtd.aprovada",
        "SGrupo_procedimento": "6",
        "formato": "table",
        "mostre": "Mostra",
    }

    for nome, esperado in esperados.items():
        if valores.get(nome) != [esperado]:
            sys.exit(f"Parametro inesperado: {nome}")

    periodos = valores.get("Arquivos", [])

    if len(periodos) != 1:
        sys.exit("Permitido exatamente um periodo.")

    periodo = periodos[0]

    if not re.fullmatch(r"qabr\d{4}\.dbf", periodo):
        sys.exit("Periodo invalido para SIA/QABR.")

    # Confirma que o periodo existe no formulario inspecionado.
    metadados = json.loads(
        Path(
            "dados/inspecao/formulario_sia_qabr.json"
        ).read_text(encoding="utf-8")
    )

    campo_arquivos = next(
        c for c in metadados["campos"]
        if c.get("name") == "Arquivos"
    )

    permitidos = {
        opcao["value"]
        for opcao in campo_arquivos["opcoes"]
    }

    if periodo not in permitidos:
        sys.exit("Periodo ausente do formulario inspecionado.")

    url = urlparse(dados["url"])

    if (
        url.hostname != "tabnet.datasus.gov.br"
        or url.path != "/cgi/tabcgi.exe"
        or url.query != "sia/cnv/qabr.def"
    ):
        sys.exit("Destino nao autorizado.")

    destino = urlunparse(
        url._replace(scheme="http", netloc="tabnet.datasus.gov.br")
    )

    if saida.exists():
        sys.exit(
            f"Arquivo de resposta ja existe: {saida}"
        )

    corpo = urlencode(
        parametros,
        encoding="iso-8859-1"
    ).encode("ascii")

    print("=== CONSULTA SIA/AM ===")
    print("Periodo:", periodo)
    print("Destino:", destino)
    print("Saida:", saida)

    if simular:
        print("Simulacao: consulta validada.")
        print("Nenhuma requisicao enviada.")
        return

    confirmar = input(
        "\nEnviar uma consulta ao DATASUS? [s/N]: "
    ).strip().lower()

    if confirmar != "s":
        print("Consulta cancelada.")
        return

    req = Request(
        destino,
        data=corpo,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=60) as resposta:
            status = resposta.status
            conteudo = resposta.read(5_000_001)
            tipo = resposta.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError) as erro:
        sys.exit(f"Falha na consulta: {erro}")

    if status != 200:
        sys.exit(f"Status inesperado: {status}")

    if len(conteudo) > 5_000_000:
        sys.exit("Resposta excedeu o limite de 5 MB.")

    if "html" not in tipo.lower():
        sys.exit(f"Tipo inesperado: {tipo}")

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_bytes(conteudo)

    print("\nResposta salva:", saida)
    print("HTTP:", status)
    print("Bytes:", len(conteudo))
    print("Resultado ainda precisa ser normalizado e validado.")



def main():
    parser = argparse.ArgumentParser(
        description="Executor de consultas DATASUS"
    )

    origem = parser.add_mutually_exclusive_group(required=True)
    origem.add_argument("--consulta")
    origem.add_argument("--competencia")

    parser.add_argument("--sistema")
    parser.add_argument("--subsistema")
    parser.add_argument("--saida", required=True)
    parser.add_argument("--simular", action="store_true")

    args = parser.parse_args()

    if args.consulta:
        if args.sistema or args.subsistema:
            parser.error(
                "--sistema e --subsistema exigem --competencia"
            )

        dados = json.loads(
            Path(args.consulta).read_text(encoding="utf-8")
        )
    else:
        if not args.sistema or not args.subsistema:
            parser.error(
                "--competencia exige --sistema e --subsistema"
            )

        from montar_consulta import montar_consulta

        dados = montar_consulta(
            args.sistema,
            args.subsistema,
            args.competencia,
        )

    executar_dados(
        dados,
        Path(args.saida),
        simular=args.simular,
    )


if __name__ == "__main__":
    main()
