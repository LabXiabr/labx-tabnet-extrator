"""CLI de catalogo de fontes - sem consultas externas nem alteracoes em dados/."""
import argparse
import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.catalogo.fontes import listar_fontes, obter_fonte


def main() -> int:
    parser = argparse.ArgumentParser(description="Catalogo de fontes LABX TabNet")
    parser.add_argument("acao", choices=["listar", "validar", "detalhar"])
    parser.add_argument("--sistema", default="SIA")
    parser.add_argument("--subsistema", default="AM")
    parser.add_argument("--permitir-nao-homologada", action="store_true")
    args = parser.parse_args()
    try:
        if args.acao in ("listar", "validar"):
            fontes = listar_fontes()
            if args.acao == "validar":
                print(f"Catalogo valido: {len(fontes)} fontes; {sum(f.homologada for f in fontes)} homologadas.")
            else:
                print(json.dumps([f.to_dict() for f in fontes], ensure_ascii=False, indent=2))
        else:
            fonte = obter_fonte(args.sistema, args.subsistema, exigir_homologada=not args.permitir_nao_homologada)
            print(json.dumps(fonte.to_dict(), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
