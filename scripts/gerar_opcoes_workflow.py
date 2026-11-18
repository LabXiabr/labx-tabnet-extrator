#!/usr/bin/env python3
"""Atualiza as opções do Actions apenas com fontes disponíveis no conversor original."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / 'catalogo' / 'fontes_sus.json'
ORIGINAL = ROOT / 'poc_dbc_online' / 'fontes.json'
WORKFLOW = ROOT / '.github' / 'workflows' / 'poc-dbc-lote-catalogo.yml'
INICIO = '        # INICIO-FONTES-GERADAS\n'
FIM = '        # FIM-FONTES-GERADAS\n'


def gerar(catalogo=CATALOGO, workflow=WORKFLOW, check=False, original=ORIGINAL):
    fontes = json.loads(Path(catalogo).read_text(encoding='utf-8'))['fontes']
    originais = json.loads(Path(original).read_text(encoding='utf-8'))['fontes']
    habilitadas = []
    for f in originais:
        codigo = f"{f['sistema']}/{f['subsistema']}"
        registro = fontes.get(codigo)
        if not registro or registro.get('revisao_necessaria') or not registro.get('diretorios'):
            continue
        if f.get('status') == 'planejada' or not f.get('diretorio_ftp'):
            continue
        if f.get('prefixo', '').upper() != registro['subsistema'].upper():
            continue
        if not any(d['url'].rstrip('/').endswith(f['diretorio_ftp'].rstrip('/')) for d in registro['diretorios']):
            continue
        habilitadas.append(codigo)
    habilitadas = sorted(set(habilitadas))
    if not habilitadas:
        raise ValueError('Nenhuma fonte compatível para executar DBC → Parquet.')
    conteudo = Path(workflow).read_text(encoding='utf-8')
    if conteudo.count(INICIO) != 1 or conteudo.count(FIM) != 1:
        raise ValueError('Marcadores de fontes ausentes ou duplicados no workflow.')
    antes, resto = conteudo.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    novo = antes + INICIO + ''.join(f'          - {v}\n' for v in habilitadas) + FIM + depois
    if check:
        if novo != conteudo:
            print('ERRO: opções desatualizadas. Execute python scripts/gerar_opcoes_workflow.py')
            return 1
        print(f'OK: {len(habilitadas)} fontes compatíveis no formulário de extração real.')
        return 0
    Path(workflow).write_text(novo, encoding='utf-8')
    print(f'Workflow atualizado com {len(habilitadas)} fontes de extração real.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raise SystemExit(gerar(check=args.check))
