#!/usr/bin/env python3
"""Sincroniza dropdown estático do Actions com fontes aptas à descoberta do catálogo."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / 'catalogo' / 'fontes_sus.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'poc-dbc-lote-catalogo.yml'
INICIO = '        # INICIO-FONTES-GERADAS\n'
FIM = '        # FIM-FONTES-GERADAS\n'


def gerar(catalogo: Path, workflow: Path, check: bool = False) -> int:
    dados = json.loads(catalogo.read_text(encoding='utf-8'))
    fontes = dados['fontes']
    codigos = sorted(
        codigo for codigo, reg in fontes.items()
        if reg.get('diretorios') and not reg.get('revisao_necessaria', False)
    )
    if not codigos or 'SIA/PA' not in codigos:
        raise ValueError('Nenhuma fonte adequada ou SIA/PA ausente; revise o catálogo')
    conteudo = workflow.read_text(encoding='utf-8')
    if conteudo.count(INICIO) != 1 or conteudo.count(FIM) != 1:
        raise ValueError('Marcadores da lista de fontes não encontrados exatamente uma vez')
    antes, resto = conteudo.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    trecho = ''.join(f'          - {codigo}\n' for codigo in codigos)
    atualizado = antes + INICIO + trecho + FIM + depois
    if check:
        if atualizado != conteudo:
            print('ERRO: opções do workflow não correspondem ao catálogo. Execute python scripts/gerar_opcoes_workflow.py')
            return 1
        print(f'OK: {len(codigos)} fontes elegíveis para descoberta estão sincronizadas.')
        return 0
    workflow.write_text(atualizado, encoding='utf-8')
    print(f'Atualizado: {len(codigos)} fontes selecionáveis; {len(fontes)-len(codigos)} fontes permanecem catalogadas, mas não liberadas para descoberta.')
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    raise SystemExit(gerar(CATALOGO, WORKFLOW, args.check))
