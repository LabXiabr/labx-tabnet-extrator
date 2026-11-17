import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from auditoria.verificar_manifesto_competencia import (
    verificar_manifesto_competencia,
)


def restaurar(inicio, fim):
    if not re.fullmatch(r"2009-(0[1-9]|1[0-2])", inicio):
        raise SystemExit("Inicio invalido")
    if not re.fullmatch(r"2009-(0[1-9]|1[0-2])", fim):
        raise SystemExit("Fim invalido")
    if inicio > fim:
        raise SystemExit("Intervalo invertido")

    pasta_origem = RAIZ / "recuperado"
    encontradas = 0

    for pasta in sorted(pasta_origem.glob("sia_am_2009??")):
        if not pasta.is_dir() or pasta.is_symlink():
            continue

        prefixo = pasta.name
        competencia = f"{prefixo[7:11]}-{prefixo[11:13]}"

        if not inicio <= competencia <= fim:
            continue

        fontes = {
            f"dados/respostas/{prefixo}.html":
                pasta / "resposta_original.html",
            f"dados/execucoes/{prefixo}/normalizado.csv":
                pasta / "normalizado.csv",
            f"dados/execucoes/{prefixo}/oficial.csv":
                pasta / "oficial.csv",
            f"dados/execucoes/{prefixo}/qualidade.json":
                pasta / "qualidade.json",
            f"dados/execucoes/{prefixo}/validacao_cruzada.json":
                pasta / "validacao_cruzada.json",
        }

        origem_manifesto = pasta / "manifesto.json"
        manifesto = json.loads(
            origem_manifesto.read_text(encoding="utf-8")
        )

        registros = manifesto.get("arquivos", [])

        if (
            manifesto.get("versao") != 1
            or manifesto.get("sistema") != "SIA"
            or manifesto.get("subsistema") != "AM"
            or manifesto.get("competencia") != competencia
            or manifesto.get("total_arquivos") != 5
            or len(registros) != 5
        ):
            raise RuntimeError(
                f"{competencia}: manifesto invalido"
            )

        if {r["caminho"] for r in registros} != set(fontes):
            raise RuntimeError(
                f"{competencia}: arquivos inesperados"
            )

        for registro in registros:
            origem = fontes[registro["caminho"]]

            if not origem.is_file() or origem.is_symlink():
                raise RuntimeError(
                    f"{competencia}: arquivo ausente"
                )

            conteudo = origem.read_bytes()
            hash_atual = hashlib.sha256(conteudo).hexdigest()

            if (
                hash_atual != registro["sha256"]
                or len(conteudo) != registro["tamanho_bytes"]
            ):
                raise RuntimeError(
                    f"{competencia}: integridade reprovada"
                )

        destinos = [
            RAIZ / caminho for caminho in fontes
        ]
        destinos.append(
            RAIZ / "dados/auditoria"
            / f"{prefixo}_manifesto.json"
        )

        if any(p.exists() for p in destinos):
            raise RuntimeError(
                f"{competencia}: destino ja existe. "
                "Nenhum arquivo sera sobrescrito."
            )

        for relativo, origem in fontes.items():
            destino = RAIZ / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)

        destino_manifesto = destinos[-1]
        destino_manifesto.parent.mkdir(
            parents=True, exist_ok=True
        )
        shutil.copy2(origem_manifesto, destino_manifesto)

        problemas = verificar_manifesto_competencia(
            RAIZ, "SIA", "AM", competencia
        )
        if problemas:
            raise RuntimeError(
                f"{competencia}: " + "; ".join(problemas)
            )

        subprocess.run(
            [
                sys.executable,
                str(RAIZ / "scripts/resumir_execucao.py"),
                competencia,
            ],
            cwd=RAIZ,
            check=True,
        )

        encontradas += 1
        print(f"{competencia}: restaurada e verificada")

    if not encontradas:
        raise SystemExit(
            "Nenhuma competencia do intervalo foi recuperada."
        )

    print(f"Total restaurado: {encontradas}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "Uso: restaurar_execucoes.py INICIO FIM"
        )

    restaurar(sys.argv[1], sys.argv[2])
