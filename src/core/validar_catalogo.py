import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[2]


def validar_catalogo(caminho):
    catalogo = json.loads(
        caminho.read_text(encoding="utf-8")
    )

    if catalogo.get("versao") != 1:
        raise ValueError("Versao de catalogo nao suportada")

    fontes = catalogo.get("fontes")

    if not isinstance(fontes, dict) or not fontes:
        raise ValueError("Catalogo sem fontes")

    for identificador, fonte in fontes.items():
        if "/" not in identificador:
            raise ValueError(
                f"Identificador invalido: {identificador}"
            )

        for campo in ("formulario", "consulta"):
            url = urlparse(fonte[campo])

            if (
                url.scheme not in ("http", "https")
                or url.hostname != "tabnet.datasus.gov.br"
            ):
                raise ValueError(
                    f"URL nao autorizada: {identificador}"
                )

        for campo in ("inspecao_local", "modelo_local"):
            relativo = Path(fonte[campo])
            local = (RAIZ / relativo).resolve()

            if (
                relativo.is_absolute()
                or not local.is_relative_to(RAIZ)
                or not local.is_file()
            ):
                raise ValueError(
                    f"Arquivo local invalido: {fonte[campo]}"
                )

        if not fonte.get("campos_saida"):
            raise ValueError("Campos de saida ausentes")

        print(f"{identificador}: catalogado e validado")

    print("Fontes cadastradas:", len(fontes))
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalogo",
        default="configuracoes/fontes.json",
    )
    args = parser.parse_args()

    validar_catalogo(Path(args.catalogo))


if __name__ == "__main__":
    main()
