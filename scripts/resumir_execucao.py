import csv
import hashlib
import json
import os
import sys
from pathlib import Path

competencia = sys.argv[1]
mes = competencia.replace("-", "")
prefixo = f"sia_am_{mes}"

pasta = Path("dados/execucoes") / prefixo
auditoria = Path("dados/auditoria") / f"{prefixo}_manifesto.json"


def ler_json(caminho):
    return json.loads(caminho.read_text(encoding="utf-8"))


def formatar(numero):
    return f"{numero:,}".replace(",", ".")


qualidade = ler_json(pasta / "qualidade.json")
validacao = ler_json(pasta / "validacao_cruzada.json")
manifesto = ler_json(auditoria)

with (pasta / "normalizado.csv").open(
    encoding="utf-8", newline=""
) as arquivo:
    registros = list(csv.DictReader(arquivo))

total_csv = sum(int(r["qt_aprovada"]) for r in registros)
ufs = {r["sg_uf"] for r in registros}
divergencias = validacao["divergencias"]

arquivos_esperados = {
    f"dados/respostas/{prefixo}.html",
    f"dados/execucoes/{prefixo}/normalizado.csv",
    f"dados/execucoes/{prefixo}/oficial.csv",
    f"dados/execucoes/{prefixo}/qualidade.json",
    f"dados/execucoes/{prefixo}/validacao_cruzada.json",
}

verificados = 0
caminhos_manifesto = {
    item["caminho"] for item in manifesto["arquivos"]
}

if caminhos_manifesto == arquivos_esperados:
    for item in manifesto["arquivos"]:
        caminho = Path(item["caminho"])
        conteudo = caminho.read_bytes()

        hash_atual = hashlib.sha256(conteudo).hexdigest()

        if (
            hash_atual == item["sha256"]
            and len(conteudo) == item["tamanho_bytes"]
        ):
            verificados += 1

aprovado = all([
    qualidade["competencia"] == competencia,
    validacao["competencia"] == competencia,
    manifesto["competencia"] == competencia,
    qualidade["status"] == "validado",
    qualidade["total_consistente"] is True,
    validacao["status"] == "aprovado",
    len(divergencias) == 0,
    total_csv == qualidade["total_calculado"],
    total_csv == qualidade["total_informado"],
    total_csv == validacao["total_extraido"],
    total_csv == validacao["total_oficial"],
    len(registros) == len(ufs),
    len(ufs) == qualidade["ufs_presentes"],
    verificados == 5,
])

situacao = "APROVADA" if aprovado else "REVISAR"

resumo = f"""# Relatorio de extracao DATASUS

## SIA/AM — {competencia}

**Situacao:** {situacao}

| Indicador | Resultado |
|---|---:|
| Total extraido | {formatar(total_csv)} |
| Total oficial | {formatar(validacao["total_oficial"])} |
| UFs presentes | {len(ufs)} |
| UFs ausentes | {len(qualidade["ufs_ausentes"])} |
| Divergencias | {len(divergencias)} |
| Arquivos SHA-256 verificados | {verificados}/5 |
| Qualidade | {qualidade["status"]} |
| Validacao cruzada | {validacao["status"]} |

**Nota:** os arquivos completos estao disponiveis em Artifacts.
"""

print(resumo)

caminho_resumo = os.environ.get("GITHUB_STEP_SUMMARY")
if caminho_resumo:
    with open(caminho_resumo, "a", encoding="utf-8") as arquivo:
        arquivo.write(resumo + "\n")

if not aprovado:
    raise SystemExit("Extracao requer revisao.")
