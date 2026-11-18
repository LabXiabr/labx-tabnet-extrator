"""Compara dois CSVs SIA/AM por competencia e UF, sem modificar as fontes."""
import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

CAMPOS = {"dt_competencia", "sg_uf", "qt_aprovada"}


def carregar(arquivo):
    dados = {}
    with Path(arquivo).open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames or not CAMPOS.issubset(leitor.fieldnames):
            raise ValueError(f"Colunas obrigatorias ausentes em {arquivo}")
        for numero, linha in enumerate(leitor, 2):
            competencia = linha["dt_competencia"].strip()
            uf = linha["sg_uf"].strip().upper()
            if not competencia or not uf:
                raise ValueError(f"Chave vazia em {arquivo}:{numero}")
            chave = (competencia, uf)
            if chave in dados:
                raise ValueError(f"Duplicidade em {arquivo}:{numero}: {chave}")
            try:
                valor = int(linha["qt_aprovada"].strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Quantidade invalida em {arquivo}:{numero}") from exc
            if valor < 0:
                raise ValueError(f"Quantidade negativa em {arquivo}:{numero}")
            dados[chave] = valor
    if not dados:
        raise ValueError(f"Arquivo sem registros: {arquivo}")
    return dados


def comparar(anterior, atual):
    linhas = []
    contagens = {"inalterado": 0, "alterado": 0, "incluido": 0, "ausente_na_nova_versao": 0}
    for competencia, uf in sorted(set(anterior) | set(atual)):
        chave = (competencia, uf)
        a = anterior.get(chave)
        b = atual.get(chave)
        if a is None:
            situacao = "incluido"
        elif b is None:
            situacao = "ausente_na_nova_versao"
        elif a != b:
            situacao = "alterado"
        else:
            situacao = "inalterado"
        contagens[situacao] += 1
        linhas.append({
            "dt_competencia": competencia,
            "sg_uf": uf,
            "qt_anterior": "" if a is None else a,
            "qt_atual": "" if b is None else b,
            "diferenca": "" if a is None or b is None else b-a,
            "situacao": situacao,
        })
    return linhas, contagens


def executar(arquivo_anterior, arquivo_atual, saida, resumo_github=False):
    anterior = carregar(arquivo_anterior)
    atual = carregar(arquivo_atual)
    linhas, contagens = comparar(anterior, atual)
    saida = Path(saida)
    # Recusar sobrescrita mesmo quando as duas saídas já existem.
    if (saida / "comparacao.csv").exists() or (saida / "comparacao.json").exists():
        raise FileExistsError("Comparacao existente preservada")
    saida.mkdir(parents=True, exist_ok=True)
    with (saida / "comparacao.csv").open("x", encoding="utf-8", newline="") as f:
        campos = ["dt_competencia", "sg_uf", "qt_anterior", "qt_atual", "diferenca", "situacao"]
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)
    relatorio = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "origem_anterior": str(arquivo_anterior),
        "origem_atual": str(arquivo_atual),
        "registros_anteriores": len(anterior),
        "registros_atuais": len(atual),
        "total_anterior": sum(anterior.values()),
        "total_atual": sum(atual.values()),
        "diferenca_total": sum(atual.values())-sum(anterior.values()),
        "contagens": contagens,
        "alteracoes_detectadas": sum(v for k, v in contagens.items() if k != "inalterado") > 0,
    }
    with (saida / "comparacao.json").open("x", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    destino_resumo = os.environ.get("GITHUB_STEP_SUMMARY") if resumo_github else None
    if destino_resumo:
        with open(destino_resumo, "a", encoding="utf-8") as f:
            f.write("\n## Comparacao DATASUS\n\n")
            f.write(f"- Total anterior: {relatorio['total_anterior']:,}\n")
            f.write(f"- Total atual: {relatorio['total_atual']:,}\n")
            f.write(f"- Alteracoes de registros: {sum(v for k, v in contagens.items() if k != 'inalterado')}\n")
    return relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anterior", required=True, type=Path)
    parser.add_argument("--atual", required=True, type=Path)
    parser.add_argument("--saida", required=True, type=Path)
    parser.add_argument("--resumo-github", action="store_true")
    args = parser.parse_args()
    executar(args.anterior, args.atual, args.saida, args.resumo_github)


if __name__ == "__main__":
    main()
