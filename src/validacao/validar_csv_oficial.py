import argparse
import csv
import json
from pathlib import Path

UFS = set(
    "RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA "
    "MG ES RJ SP PR SC RS MS MT GO DF".split()
)

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril",
    "Maio", "Junho", "Julho", "Agosto",
    "Setembro", "Outubro", "Novembro", "Dezembro"
]


def validar_valor(valor):
    if not valor.isdecimal():
        raise ValueError(f"Quantidade invalida: {valor!r}")
    return int(valor)


def carregar_oficial(caminho, competencia):
    texto = caminho.read_bytes().decode("iso-8859-1")
    ano, mes = map(int, competencia.split("-"))
    rotulo = f"..{MESES[mes - 1]}/{ano}"

    if "Grupo procedimento: 06 Medicamentos" not in texto:
        raise ValueError("Filtro do CSV oficial inesperado")

    abreviacoes = [
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez"
    ]

    if not 1 <= mes <= 12:
        raise ValueError("Mes invalido")

    periodo_esperado = f"Período:{abreviacoes[mes - 1]}/{ano}"

    if periodo_esperado not in texto:
        raise ValueError(
            "Periodo do CSV oficial nao corresponde a consulta"
        )

    linhas = list(csv.reader(texto.splitlines(), delimiter=";"))

    cabecalhos = [
        (i, linha)
        for i, linha in enumerate(linhas)
        if linha and linha[0].strip() == "Ano/mês processamento"
    ]

    if len(cabecalhos) != 1:
        raise ValueError("Cabecalho oficial nao identificado")

    indice, cabecalho = cabecalhos[0]
    ufs = [uf.strip() for uf in cabecalho[1:-1]]

    if (
        cabecalho[-1].strip() != "Total"
        or not ufs
        or len(ufs) != len(set(ufs))
        or set(ufs) - UFS
    ):
        raise ValueError("Colunas oficiais invalidas")

    candidatas = [
        linha for linha in linhas[indice + 1:]
        if linha and linha[0].strip() == rotulo
    ]

    if len(candidatas) != 1:
        raise ValueError("Linha mensal oficial nao identificada")

    linha = candidatas[0]

    if len(linha) != len(ufs) + 2:
        raise ValueError("Quantidade de colunas inconsistente")

    valores = {
        uf: validar_valor(valor.strip())
        for uf, valor in zip(ufs, linha[1:-1])
    }

    total = validar_valor(linha[-1].strip())

    if sum(valores.values()) != total:
        raise ValueError("Total do CSV oficial inconsistente")

    return valores, total


def carregar_extraido(caminho, competencia):
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)

        if leitor.fieldnames != [
            "sg_uf", "dt_competencia", "qt_aprovada"
        ]:
            raise ValueError("Cabecalho do CSV extraido invalido")

        registros = list(leitor)

    valores = {}

    for registro in registros:
        uf = registro["sg_uf"]

        if uf not in UFS or uf in valores:
            raise ValueError(f"UF invalida ou duplicada: {uf}")

        if registro["dt_competencia"] != competencia + "-01":
            raise ValueError("Competencia extraida incorreta")

        valores[uf] = validar_valor(registro["qt_aprovada"])

    if not valores:
        raise ValueError("CSV extraido sem registros")

    return valores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oficial", required=True)
    parser.add_argument("--extraido", required=True)
    parser.add_argument("--competencia", required=True)
    parser.add_argument("--saida", required=True)
    args = parser.parse_args()

    oficial, total = carregar_oficial(
        Path(args.oficial), args.competencia
    )

    extraido = carregar_extraido(
        Path(args.extraido), args.competencia
    )

    divergencias = []

    for uf in sorted(set(oficial) | set(extraido)):
        esperado = oficial.get(uf)
        encontrado = extraido.get(uf)

        if esperado != encontrado:
            divergencias.append({
                "uf": uf,
                "valor_oficial": esperado,
                "valor_extraido": encontrado
            })

    total_extraido = sum(extraido.values())

    aprovado = (
        not divergencias
        and total_extraido == total
    )

    relatorio = {
        "competencia": args.competencia,
        "fonte": "DATASUS TabNet publico",
        "total_oficial": total,
        "total_extraido": total_extraido,
        "ufs_oficial": len(oficial),
        "ufs_extraidas": len(extraido),
        "ufs_ausentes_na_fonte": sorted(UFS - set(oficial)),
        "divergencias": divergencias,
        "status": "aprovado" if aprovado else "divergente"
    }

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)

    saida.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print("=== VALIDACAO CRUZADA ===")
    print("Competencia:", args.competencia)
    print("UFs oficiais:", len(oficial))
    print("UFs extraidas:", len(extraido))
    print("Total oficial:", total)
    print("Total extraido:", total_extraido)
    print("Divergencias:", len(divergencias))
    print("Status:", relatorio["status"])
    print("Relatorio:", saida)

    if not aprovado:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
