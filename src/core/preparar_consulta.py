import json
from pathlib import Path
from urllib.parse import urljoin, urlencode

ARQUIVO = Path("dados/inspecao/formulario_sia_qabr.json")

CONSULTA = {
    "Linha": "Ano/mês_processamento",
    "Coluna": "UF",
    "Incremento": "Qtd.aprovada",
    "Arquivos": "qabr0801.dbf",
    "SGrupo_procedimento": "6"
}


def carregar_formulario(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def preparar_parametros(dados, configuracao):
    campos = {
        campo["name"]: campo
        for campo in dados["campos"]
        if campo.get("name") and "opcoes" in campo
    }

    parametros = []

    for nome, campo in campos.items():
        opcoes = campo["opcoes"]

        if not opcoes:
            continue

        valores_disponiveis = {
            opcao["value"] for opcao in opcoes
        }

        if nome in configuracao:
            valores = configuracao[nome]
            if not isinstance(valores, list):
                valores = [valores]
        else:
            valores = [
                opcao["value"]
                for opcao in opcoes
                if opcao.get("selected")
            ]

        for valor in valores:
            if valor not in valores_disponiveis:
                raise ValueError(
                    f"Valor inválido para {nome}: {valor}"
                )

            parametros.append((nome, valor))

    campos_desconhecidos = set(configuracao) - set(campos)

    if campos_desconhecidos:
        raise ValueError(
            f"Campos não encontrados: {campos_desconhecidos}"
        )

    return parametros


def main():
    dados = carregar_formulario(ARQUIVO)

    formulario = dados["formularios"][0]

    destino = urljoin(
        dados["url"],
        formulario["action"]
    )

    parametros = preparar_parametros(dados, CONSULTA)

    print("=== CONSULTA PREPARADA ===")
    print("Método:", formulario["method"])
    print("Destino:", destino)

    print("\nPARÂMETROS PRINCIPAIS:")
    for nome, valor in parametros:
        if nome in CONSULTA:
            print(f"{nome} = {valor}")

    print("\nTotal de parâmetros:", len(parametros))

    saida = Path("dados/consultas")
    saida.mkdir(parents=True, exist_ok=True)

    resultado = {
        "metodo": formulario["method"],
        "url": destino,
        "parametros": parametros,
        "status": "simulacao"
    }

    arquivo = saida / "sia_am_200801.json"

    arquivo.write_text(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\nConsulta salva:", arquivo)
    print("Nenhuma requisição POST foi enviada.")


if __name__ == "__main__":
    main()
