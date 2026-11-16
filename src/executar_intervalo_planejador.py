import csv
import argparse
import json
from datetime import datetime
from pathlib import Path

from core.caminhos import nome_execucao

RAIZ = Path(__file__).resolve().parents[1]


def listar_competencias(inicio, fim):
    def validar(valor):
        data = datetime.strptime(valor, "%Y-%m")
        if data.strftime("%Y-%m") != valor:
            raise ValueError("Use o formato AAAA-MM")
        return data.year, data.month

    ano, mes = validar(inicio)
    ultimo = validar(fim)

    if (ano, mes) > ultimo:
        raise ValueError("Periodo inicial maior que o final")

    while (ano, mes) <= ultimo:
        yield f"{ano:04d}-{mes:02d}"

        mes += 1
        if mes == 13:
            ano += 1
            mes = 1


from validacao.verificar_competencia import (
    UFS_VALIDAS,
    verificar_competencia as verificar_competencia_dados,
)


def verificar_competencia(competencia):
    return verificar_competencia_dados(
        competencia, RAIZ
    )

def main():
    parser = argparse.ArgumentParser(
        description="Planejamento de intervalos SIA/AM"
    )
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)

    args = parser.parse_args()

    competencias = list(
        listar_competencias(args.inicio, args.fim)
    )

    aprovadas = 0
    pendentes = 0

    print("\n=== PLANEJAMENTO DO INTERVALO ===")

    for competencia in competencias:
        if verificar_competencia(competencia):
            print(f"{competencia}: APROVADA")
            aprovadas += 1
        else:
            print(f"{competencia}: PENDENTE")
            pendentes += 1

    print("\n=== RESUMO ===")
    print("Total de competencias:", len(competencias))
    print("Aprovadas:", aprovadas)
    print("Pendentes:", pendentes)
    print("Nenhuma consulta foi executada.")


if __name__ == "__main__":
    main()
