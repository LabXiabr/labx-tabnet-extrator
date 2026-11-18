"""Separa o resultado restaurado da nova extracao no runner do GitHub."""
import os
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def competencias(inicio, fim):
    formato = r"2009-(0[1-9]|1[0-2])"
    if not re.fullmatch(formato, inicio) or not re.fullmatch(formato, fim) or inicio > fim:
        raise ValueError("Intervalo invalido")
    return [f"2009-{i:02d}" for i in range(int(inicio[-2:]), int(fim[-2:]) + 1)]


def preservar(inicio, fim, raiz=RAIZ):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Operacao permitida somente no runner do GitHub Actions")
    raiz = Path(raiz)
    meses = competencias(inicio, fim)
    trabalhos = []
    for competencia in meses:
        prefixo = f"sia_am_{competencia.replace('-', '')}"
        destino = raiz / "anteriores" / prefixo
        caminhos = [
            (raiz / "dados/execucoes" / prefixo, destino / "execucao"),
            (raiz / "dados/respostas" / f"{prefixo}.html", destino / "resposta_original.html"),
            (raiz / "dados/auditoria" / f"{prefixo}_manifesto.json", destino / "manifesto.json"),
        ]
        for origem, final in caminhos:
            if not origem.exists() or origem.is_symlink():
                raise RuntimeError(f"Referencia incompleta: {origem}")
            if final.exists() or final.is_symlink():
                raise FileExistsError(f"Destino protegido: {final}")
        trabalhos.extend(caminhos)
    # Todas as referencias sao validadas antes de mover o primeiro arquivo.
    for origem, destino in trabalhos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), str(destino))
    print(f"Referencias preservadas: {len(meses)}. Novas consultas estao liberadas.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: preservar_referencia.py INICIO FIM")
    preservar(sys.argv[1], sys.argv[2])
