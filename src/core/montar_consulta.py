import argparse
import json
from datetime import datetime
from pathlib import Path

from selecionar_fonte import selecionar_fonte

RAIZ = Path(__file__).resolve().parents[2]


def montar_consulta(sistema, subsistema, competencia):
    fonte = selecionar_fonte(sistema, subsistema)

    data = datetime.strptime(competencia, "%Y-%m")

    if data.strftime("%Y-%m") != competencia:
        raise ValueError("Competencia invalida")

    if fonte["formato_competencia"] != "AAMM":
        raise ValueError("Formato de competencia nao suportado")

    prefixo = fonte["arquivo_prefixo"]
    extensao = fonte["arquivo_extensao"]

    arquivo_periodo = (
        f"{prefixo}{data.year % 100:02d}"
        f"{data.month:02d}{extensao}"
    )

    inspecao_path = RAIZ / fonte["inspecao_local"]
    modelo_path = RAIZ / fonte["modelo_local"]

    inspecao = json.loads(
        inspecao_path.read_text(encoding="utf-8")
    )

    modelo = json.loads(
        modelo_path.read_text(encoding="utf-8")
    )

    campos = [
        campo for campo in inspecao["campos"]
        if campo.get("name") == "Arquivos"
    ]

    if len(campos) != 1:
        raise ValueError("Campo Arquivos nao identificado")

    disponiveis = {
        opcao["value"]
        for opcao in campos[0]["opcoes"]
    }

    if arquivo_periodo not in disponiveis:
        raise ValueError(
            f"Competencia indisponivel: {competencia}"
        )

    consulta = json.loads(json.dumps(modelo))

    parametros = consulta["parametros"]

    if sum(
        nome == "Arquivos"
        for nome, _ in parametros
    ) != 1:
        raise ValueError("Modelo de consulta invalido")

    consulta["parametros"] = [
        [
            nome,
            arquivo_periodo if nome == "Arquivos" else valor
        ]
        for nome, valor in parametros
    ]

    consulta["status"] = "gerada_em_memoria"

    return consulta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sistema", required=True)
    parser.add_argument("--subsistema", required=True)
    parser.add_argument("--competencia", required=True)
    args = parser.parse_args()

    consulta = montar_consulta(
        args.sistema,
        args.subsistema,
        args.competencia,
    )

    print(json.dumps(
        consulta, ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    main()
