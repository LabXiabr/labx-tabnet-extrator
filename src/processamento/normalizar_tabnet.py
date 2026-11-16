import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


UFS_VALIDAS = set(
    "RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA "
    "MG ES RJ SP PR SC RS MS MT GO DF".split()
)

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril",
    "Maio", "Junho", "Julho", "Agosto",
    "Setembro", "Outubro", "Novembro", "Dezembro"
]


def numero_inteiro(texto):
    texto = texto.strip()

    if not re.fullmatch(r"\d+|\d{1,3}(?:\.\d{3})+", texto):
        raise ValueError(f"Valor numerico invalido: {texto!r}")

    return int(texto.replace(".", ""))


def celulas(linha):
    return [
        c.get_text(" ", strip=True)
        for c in linha.find_all(
            ["th", "td"], recursive=False
        )
    ]


def extrair_registros(html, competencia, grupo="6"):
    data = datetime.strptime(competencia, "%Y-%m")

    if not 2008 <= data.year <= 2099:
        raise ValueError(
            "Esta versao suporta apenas o formulario "
            "SIA/QABR de 2008 em diante"
        )

    periodo = data.strftime("%y%m")
    nome_mes = MESES[data.month - 1]
    rotulo_mes = f"{nome_mes}/{data.year}"

    metadados = (
        "Def=sia/cnv/qabr.def",
        "Linha=Ano/mês_processamento",
        "Coluna=UF",
        "Incremento=Qtd.aprovada",
        f"SGrupo_procedimento={grupo}",
        f"Periodo={periodo}",
    )

    for item in metadados:
        if item not in html:
            raise ValueError(
                f"Metadado ausente ou incorreto: {item}"
            )

    soup = BeautifulSoup(html, "html5lib")

    linhas = [
        celulas(tr)
        for tr in soup.find_all("tr")
    ]

    cabecalhos = [
        linha for linha in linhas
        if len(linha) >= 3
        and linha[0] == "Ano/mês processamento"
        and linha[-1] == "Total"
    ]

    if len(cabecalhos) != 1:
        raise ValueError(
            "Esperado exatamente um cabecalho de UFs"
        )

    ufs = cabecalhos[0][1:-1]

    if len(ufs) != len(set(ufs)):
        raise ValueError("UFs duplicadas no cabecalho")

    desconhecidas = set(ufs) - UFS_VALIDAS

    if desconhecidas:
        raise ValueError(
            f"UFs desconhecidas: {sorted(desconhecidas)}"
        )

    if not ufs:
        raise ValueError("Nenhuma UF encontrada")

    ausentes = sorted(UFS_VALIDAS - set(ufs))

    if ausentes:
        print(
            "AVISO: UFs ausentes na resposta:",
            ", ".join(ausentes)
        )
        print(
            "Essas ausencias nao serao convertidas em zero."
        )

    candidatas = [
        linha for linha in linhas
        if linha
        and linha[0].lstrip(".").strip() == rotulo_mes
    ]

    if len(candidatas) != 1:
        raise ValueError(
            f"Esperada uma linha de {rotulo_mes}; "
            f"encontradas {len(candidatas)}"
        )

    linha = candidatas[0]

    if len(linha) != len(ufs) + 2:
        raise ValueError(
            f"Quantidade inesperada de celulas: {len(linha)}"
        )

    valores = [
        numero_inteiro(valor)
        for valor in linha[1:-1]
    ]

    total_informado = numero_inteiro(linha[-1])
    total_calculado = sum(valores)

    if total_calculado != total_informado:
        raise ValueError(
            f"Total divergente: "
            f"calculado={total_calculado}, "
            f"informado={total_informado}"
        )

    registros = [
        {
            "sg_uf": uf,
            "dt_competencia": data.strftime("%Y-%m-01"),
            "qt_aprovada": quantidade,
        }
        for uf, quantidade in zip(ufs, valores)
    ]

    return registros, total_informado


def main():
    parser = argparse.ArgumentParser(
        description="Normalizador TabNet SIA/QABR"
    )

    parser.add_argument("--entrada", required=True)
    parser.add_argument("--saida", required=True)
    parser.add_argument(
        "--competencia",
        required=True,
        help="Formato AAAA-MM"
    )
    parser.add_argument(
        "--grupo",
        default="6",
        help="Valor do grupo no formulario"
    )

    args = parser.parse_args()

    entrada = Path(args.entrada)
    saida = Path(args.saida)

    html = entrada.read_bytes().decode(
        "iso-8859-1", errors="replace"
    )

    registros, total = extrair_registros(
        html,
        args.competencia,
        args.grupo
    )

    saida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with saida.open(
        "w", encoding="utf-8", newline=""
    ) as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=[
                "sg_uf",
                "dt_competencia",
                "qt_aprovada"
            ]
        )

        escritor.writeheader()
        escritor.writerows(registros)

    print("NORMALIZACAO CONCLUIDA")
    print("Competencia:", args.competencia)
    print("Grupo:", args.grupo)
    print("UFs:", len(registros))
    print("Total nacional:", total)
    print("Arquivo:", saida)


if __name__ == "__main__":
    main()
