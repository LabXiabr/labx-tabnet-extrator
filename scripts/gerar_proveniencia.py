"""Gera comprovante de proveniencia sem sobrescrever arquivo existente."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.catalogo.fontes import obter_fonte


def gerar(fonte, competencia: str, arquivo_csv: Path, saida: Path, *, commit: str | None = None, run_id: str | None = None) -> dict:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", competencia):
        raise ValueError("Competencia invalida; use AAAA-MM")
    if not fonte.homologada:
        raise ValueError("Fonte nao homologada")
    arquivo_csv = Path(arquivo_csv)
    saida = Path(saida)
    if not arquivo_csv.is_file() or not arquivo_csv.stat().st_size:
        raise FileNotFoundError("CSV ausente ou vazio")
    if saida.exists():
        raise FileExistsError(f"Proveniencia ja existe, preservada: {saida}")
    sha = hashlib.sha256()
    with arquivo_csv.open("rb") as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
            sha.update(bloco)
    comprovante = {
        "schema_version": 1,
        "fonte": fonte.to_dict(),
        "competencia": competencia,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "arquivo_csv": str(arquivo_csv),
        "csv_sha256": sha.hexdigest(),
        "git_commit": commit,
        "github_run_id": run_id,
        "observacao": "Proveniencia do arquivo; nao substitui auditoria oficial nem comprova nova consulta de rede.",
    }
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("x", encoding="utf-8") as destino:
        json.dump(comprovante, destino, ensure_ascii=False, indent=2)
        destino.write("\n")
    return comprovante


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sistema", default="SIA")
    parser.add_argument("--subsistema", default="AM")
    parser.add_argument("--competencia", required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    fonte = obter_fonte(args.sistema, args.subsistema)
    gerado = gerar(fonte, args.competencia, args.csv, args.saida, commit=os.getenv("GITHUB_SHA"), run_id=os.getenv("GITHUB_RUN_ID"))
    print(json.dumps(gerado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
