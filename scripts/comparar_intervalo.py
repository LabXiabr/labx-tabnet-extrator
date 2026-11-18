"""Compara cada competencia nova com a referencia preservada e anexa os relatorios."""
import json
import shutil
import sys
from pathlib import Path

from comparar_versoes import executar
from preservar_referencia import competencias

RAIZ = Path(__file__).resolve().parents[1]


def comparar_intervalo(inicio, fim, raiz=RAIZ):
    raiz = Path(raiz)
    meses = competencias(inicio, fim)
    pacote = raiz / "pacote"
    if not pacote.is_dir() or not (pacote / "consolidado.csv").is_file():
        raise RuntimeError("Pacote validado/consolidado nao encontrado")
    saida_final = pacote / "comparacoes"
    if saida_final.exists():
        raise FileExistsError("Comparacoes ja existentes")
    tarefas = []
    for comp in meses:
        nome = f"sia_am_{comp.replace('-', '')}"
        anterior = raiz / "anteriores" / nome
        atual = raiz / "dados/execucoes" / nome / "normalizado.csv"
        if not (anterior / "execucao/normalizado.csv").is_file() or not atual.is_file():
            raise RuntimeError(f"Arquivos incompletos para comparar: {comp}")
        tarefas.append((nome, anterior, atual))
    saida_final.mkdir(parents=True)
    totais = {"inalterado": 0, "alterado": 0, "incluido": 0, "ausente_na_nova_versao": 0}
    for nome, anterior, atual in tarefas:
        destino = saida_final / nome
        resultado = executar(anterior / "execucao/normalizado.csv", atual, destino)
        for chave in totais:
            totais[chave] += resultado["contagens"][chave]
        # Inclui a referencia completa dentro de um subdiretorio versionado do ZIP.
        shutil.copytree(anterior, destino / "versao_anterior")
    resumo = {"competencias_comparadas": len(tarefas), "contagens": totais,
              "alteracoes_detectadas": any(totais[k] for k in totais if k != "inalterado")}
    (saida_final / "resumo_intervalo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return resumo


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: comparar_intervalo.py INICIO FIM")
    comparar_intervalo(sys.argv[1], sys.argv[2])
