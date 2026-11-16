import argparse
import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from validacao.verificar_competencia import verificar_competencia

RAIZ = Path(__file__).resolve().parents[2]
CAMPOS = ["sg_uf", "dt_competencia", "qt_aprovada"]


def competencias(inicio, fim):
    def validar(valor):
        data = datetime.strptime(valor, "%Y-%m")
        if data.strftime("%Y-%m") != valor:
            raise ValueError("Use AAAA-MM")
        return data.year, data.month

    ano, mes = validar(inicio)
    ultimo = validar(fim)

    if (ano, mes) > ultimo:
        raise ValueError("Periodo inicial maior que o final")

    while (ano, mes) <= ultimo:
        yield f"{ano:04d}-{mes:02d}"
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1


def consolidar(inicio, fim):
    todos = []
    chaves = set()
    resumo = []

    for competencia in competencias(inicio, fim):
        if not verificar_competencia(competencia, RAIZ):
            raise ValueError(
                f"{competencia}: integridade insuficiente "
                "para consolidacao"
            )
        nome = "sia_am_" + competencia.replace("-", "")
        pasta = RAIZ / "dados/execucoes" / nome

        csv_arquivo = pasta / "normalizado.csv"
        validacao = pasta / "validacao_cruzada.json"
        qualidade = pasta / "qualidade.json"

        for arquivo in [csv_arquivo, validacao, qualidade]:
            if not arquivo.is_file():
                raise ValueError(
                    f"{competencia}: falta {arquivo.name}. "
                    "Consolidacao interrompida."
                )

        cruzada = json.loads(validacao.read_text(encoding="utf-8"))
        relatorio = json.loads(qualidade.read_text(encoding="utf-8"))

        if (
            cruzada.get("status") != "aprovado"
            or cruzada.get("competencia") != competencia
            or relatorio.get("competencia") != competencia
            or relatorio.get("total_consistente") is not True
        ):
            raise ValueError(f"{competencia}: validacao insuficiente")

        with csv_arquivo.open(encoding="utf-8", newline="") as f:
            leitor = csv.DictReader(f)
            if leitor.fieldnames != CAMPOS:
                raise ValueError(f"{competencia}: colunas inesperadas")
            registros = list(leitor)

        total_mes = 0

        for registro in registros:
            uf = registro["sg_uf"]
            chave = (uf, registro["dt_competencia"])

            if registro["dt_competencia"] != competencia + "-01":
                raise ValueError("Competencia divergente no CSV")

            if chave in chaves:
                raise ValueError(f"Registro duplicado: {chave}")

            chaves.add(chave)

            valor = registro["qt_aprovada"]
            if not valor.isdecimal():
                raise ValueError(f"Quantidade invalida: {valor}")

            total_mes += int(valor)
            todos.append(registro)

        if (
            len(registros) != cruzada["ufs_extraidas"]
            or total_mes != cruzada["total_extraido"]
            or total_mes != relatorio["total_calculado"]
        ):
            raise ValueError(f"{competencia}: totais divergentes")

        resumo.append({
            "competencia": competencia,
            "registros": len(registros),
            "total": total_mes,
            "ufs_ausentes": relatorio["ufs_ausentes"],
        })

        print(f"{competencia}: {len(registros)} UFs, total {total_mes}")

    destino = RAIZ / "dados/consolidados"
    destino.mkdir(parents=True, exist_ok=True)

    nome = f"sia_am_{inicio.replace('-', '')}_{fim.replace('-', '')}"
    csv_final = destino / f"{nome}.csv"
    json_final = destino / f"{nome}_qualidade.json"

    if csv_final.exists() or json_final.exists():
        raise FileExistsError("Consolidacao ja existe; arquivos preservados")

    # Prepara as duas saidas antes de publicar o resultado.
    with tempfile.TemporaryDirectory(dir=destino) as pasta:
        pasta = Path(pasta)
        temp_csv = pasta / "consolidado.csv"
        temp_json = pasta / "qualidade.json"

        with temp_csv.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS)
            escritor.writeheader()
            escritor.writerows(todos)

        temp_json.write_text(
            json.dumps({
                "inicio": inicio,
                "fim": fim,
                "competencias": resumo,
                "registros": len(todos),
                "total_geral": sum(x["total"] for x in resumo),
                "status": "consolidado_de_fontes_validadas",
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        os.replace(temp_csv, csv_final)
        os.replace(temp_json, json_final)

    print("\nCONSOLIDACAO CONCLUIDA")
    print("Competencias:", len(resumo))
    print("Registros:", len(todos))
    print("CSV:", csv_final)
    print("Qualidade:", json_final)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)
    args = parser.parse_args()
    consolidar(args.inicio, args.fim)
