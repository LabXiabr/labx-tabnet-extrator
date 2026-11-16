import argparse
import json
from pathlib import Path

try:
    from .validar_catalogo import validar_catalogo
except ImportError:
    from validar_catalogo import validar_catalogo

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "configuracoes/fontes.json"


def selecionar_fonte(sistema, subsistema):
    sistema = sistema.strip().upper()
    subsistema = subsistema.strip().upper()

    if not sistema.isalpha() or not subsistema.isalpha():
        raise ValueError("Sistema ou subsistema invalido")

    validar_catalogo(CATALOGO)

    dados = json.loads(
        CATALOGO.read_text(encoding="utf-8")
    )

    identificador = f"{sistema}/{subsistema}"

    fonte = dados["fontes"].get(identificador)

    if fonte is None:
        disponiveis = ", ".join(
            sorted(dados["fontes"])
        )
        raise ValueError(
            f"Fonte nao cadastrada: {identificador}. "
            f"Disponiveis: {disponiveis}"
        )

    return fonte


def main():
    parser = argparse.ArgumentParser(
        description="Selecionar fonte publica DATASUS"
    )
    parser.add_argument("--sistema", required=True)
    parser.add_argument("--subsistema", required=True)

    args = parser.parse_args()

    fonte = selecionar_fonte(
        args.sistema,
        args.subsistema,
    )

    print("\n=== FONTE SELECIONADA ===")
    print("Sistema:", args.sistema.upper())
    print("Subsistema:", args.subsistema.upper())
    print("Descricao:", fonte["descricao"])
    print("Status:", fonte["status"])
    print("Formulario:", fonte["formulario"])
    print("Prefixo:", fonte["arquivo_prefixo"])
    print("Inicio validado:", fonte["inicio_validado"])
    print("Fim validado:", fonte["fim_validado"])
    print("Nenhuma consulta foi enviada.")


if __name__ == "__main__":
    main()
