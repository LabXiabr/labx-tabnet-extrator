import argparse
import json
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]

MODELO = (
    RAIZ / "dados/consultas/sia_am_200802.json"
)

INSPECAO = (
    RAIZ / "dados/inspecao/formulario_sia_qabr.json"
)

DESTINO = RAIZ / "dados/consultas"


def interpretar_mes(valor):
    data = datetime.strptime(valor, "%Y-%m")

    if data.strftime("%Y-%m") != valor:
        raise ValueError("Use o formato AAAA-MM")

    if not 2008 <= data.year <= 2099:
        raise ValueError("Ano fora do intervalo QABR")

    return data.year, data.month


def listar_competencias(inicio, fim):
    ano, mes = interpretar_mes(inicio)
    ano_final, mes_final = interpretar_mes(fim)

    if (ano, mes) > (ano_final, mes_final):
        raise ValueError("Periodo inicial maior que o final")

    competencias = []

    while (ano, mes) <= (ano_final, mes_final):
        competencias.append(f"{ano:04d}-{mes:02d}")

        mes += 1

        if mes == 13:
            ano += 1
            mes = 1

    return competencias


def arquivos_disponiveis():
    dados = json.loads(
        INSPECAO.read_text(encoding="utf-8")
    )

    campos = [
        campo
        for campo in dados["campos"]
        if campo.get("name") == "Arquivos"
    ]

    if len(campos) != 1:
        raise ValueError(
            "Campo Arquivos nao identificado"
        )

    return {
        opcao["value"]
        for opcao in campos[0]["opcoes"]
    }


def gerar_consulta(modelo, competencia):
    ano, mes = interpretar_mes(competencia)

    arquivo_periodo = f"qabr{ano % 100:02d}{mes:02d}.dbf"

    copia = json.loads(json.dumps(modelo))

    parametros = copia["parametros"]

    if sum(
        nome == "Arquivos"
        for nome, _ in parametros
    ) != 1:
        raise ValueError(
            "Modelo deve conter um unico periodo"
        )

    copia["parametros"] = [
        [
            nome,
            arquivo_periodo if nome == "Arquivos" else valor
        ]
        for nome, valor in parametros
    ]

    copia["status"] = "gerada_automaticamente"

    return copia, arquivo_periodo


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de consultas SIA/QABR"
    )

    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)

    parser.add_argument(
        "--gravar",
        action="store_true",
        help="Grava as configuracoes em JSON"
    )

    args = parser.parse_args()

    competencias = listar_competencias(
        args.inicio, args.fim
    )

    modelo = json.loads(
        MODELO.read_text(encoding="utf-8")
    )

    disponiveis = arquivos_disponiveis()

    DESTINO.mkdir(parents=True, exist_ok=True)

    novas = 0
    existentes = 0
    indisponiveis = 0

    for competencia in competencias:
        consulta, arquivo_periodo = gerar_consulta(
            modelo, competencia
        )

        if arquivo_periodo not in disponiveis:
            print(
                f"{competencia}: indisponivel no formulario"
            )
            indisponiveis += 1
            continue

        identificador = competencia.replace("-", "")

        destino = (
            DESTINO / f"sia_am_{identificador}.json"
        )

        if destino.exists():
            anterior = json.loads(
                destino.read_text(encoding="utf-8")
            )

            if (
                anterior.get("parametros")
                != consulta["parametros"]
            ):
                raise ValueError(
                    f"Configuracao existente divergente: {destino}"
                )

            print(f"{competencia}: ja existe")
            existentes += 1
            continue

        if args.gravar:
            destino.write_text(
                json.dumps(
                    consulta,
                    ensure_ascii=False,
                    indent=2
                ) + "\n",
                encoding="utf-8"
            )

            print(f"{competencia}: configuracao criada")

        else:
            print(f"{competencia}: pronta para gerar")

        novas += 1

    print("\n=== RESUMO ===")
    print("Competencias solicitadas:", len(competencias))
    print("Novas:", novas)
    print("Ja existentes:", existentes)
    print("Indisponiveis:", indisponiveis)
    print("Gravacao ativada:", args.gravar)


if __name__ == "__main__":
    main()
