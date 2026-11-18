#!/usr/bin/env python3
"""Prepara matriz mensal e executa lotes reais usando o robô existente.

Não altera o robô, o catálogo nem o conteúdo das saídas já existentes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / 'catalogo' / 'fontes_sus.json'
ORIGINAL = ROOT / 'poc_dbc_online' / 'fontes.json'
ROBO = ROOT / 'poc_dbc_online' / 'robo.py'
UF = 'AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split()


def competencias(valor):
    if re.fullmatch(r'20\d{2}', valor):
        ano = int(valor)
        meses = [f'{ano}-{m:02d}' for m in range(1, 13)]
    elif re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', valor):
        meses = [valor]
    else:
        raise ValueError('Competência inválida. Informe AAAA ou AAAA-MM (a partir de 2000).')
    if meses[0] > datetime.now(timezone.utc).strftime('%Y-%m'):
        raise ValueError('Competência futura não permitida.')
    return meses


def fonte_compativel(codigo, comps, caminho_catalogo=CATALOGO, caminho_original=ORIGINAL):
    if not re.fullmatch(r'[A-Z0-9_]+/[A-Z0-9_]+', codigo):
        raise ValueError('Fonte inválida; use SISTEMA/SUBSISTEMA.')
    atual = json.loads(caminho_catalogo.read_text(encoding='utf-8'))['fontes']
    reg = atual.get(codigo)
    if not reg or reg.get('revisao_necessaria') or not reg.get('diretorios'):
        raise ValueError(f'{codigo} não está apta no catálogo ampliado.')
    originais = json.loads(caminho_original.read_text(encoding='utf-8'))['fontes']
    compativeis = [f for f in originais if f.get('sistema') == reg['sistema'] and f.get('subsistema') == reg['subsistema']]
    if len(compativeis) != 1 or compativeis[0].get('status') == 'planejada':
        raise ValueError(f'{codigo} cadastrada, mas ainda não habilitada para extração real pelo robô original.')
    original = compativeis[0]
    prefixo = original.get('prefixo', '')
    diretorio = original.get('diretorio_ftp')
    if not diretorio or prefixo.upper() != reg['subsistema'].upper():
        raise ValueError(f'{codigo}: configuração de conversão incompatível com catálogo ampliado.')
    if original.get('inicio') and min(comps) < original['inicio']:
        raise ValueError(f'{codigo}: competência anterior ao início do robô: {original["inicio"]}.')
    if max(comps) > datetime.now(timezone.utc).strftime('%Y-%m'):
        raise ValueError('Competência futura.')
    for comp in comps:
        valor = int(comp.replace('-', ''))
        urls = []
        for d in reg['diretorios']:
            url = d['url']
            janelas = re.findall(r'(\d{6})_(\d{6})?', url)
            if janelas:
                ini, fim = janelas[-1]
                if valor < int(ini) or (fim and valor > int(fim)):
                    continue
            urls.append(urlsplit(url).path.rstrip('/'))
        if diretorio.rstrip('/') not in urls:
            raise ValueError(f'{codigo}: diretório do robô não coincide com o catálogo para {comp}.')
    return reg


def matriz(codigo, comp_texto, tamanho_lote=3):
    comps = competencias(comp_texto)
    fonte_compativel(codigo, comps)
    if tamanho_lote < 1 or tamanho_lote > 3:
        raise ValueError('Tamanho do lote deve ser de 1 a 3 UFs.')
    entradas = [dict(competencia=comp, ufs='-'.join(UF[i:i+tamanho_lote]))
                for comp in comps for i in range(0, len(UF), tamanho_lote)]
    if len(entradas) > 256:
        raise ValueError('A matriz excede o limite de 256 jobs do GitHub Actions.')
    return {'include': entradas}


def hash_arquivo(caminho):
    h = hashlib.sha256()
    with caminho.open('rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def conferir_saida(pasta, codigo, uf, competencia):
    arq = pasta / 'manifesto.json'
    if not arq.is_file():
        raise RuntimeError('Manifesto ausente')
    m = json.loads(arq.read_text(encoding='utf-8'))
    sistema, subsistema = codigo.split('/')
    if (m.get('sistema'), m.get('subsistema'), m.get('uf'), m.get('competencia')) != (sistema, subsistema, uf, competencia):
        raise RuntimeError('Manifesto não corresponde à fonte/UF/competência')
    if not m.get('arquivos'):
        raise RuntimeError('Manifesto sem arquivos')
    total = 0
    for item in m['arquivos']:
        parquet = pasta / item['parquet']
        if not parquet.is_file() or parquet.stat().st_size == 0:
            raise RuntimeError(f'Parquet ausente/vazio: {parquet.name}')
        if hash_arquivo(parquet) != item['sha256_parquet']:
            raise RuntimeError(f'Hash Parquet divergente: {parquet.name}')
        if item['registros_dbf'] != item['registros_parquet']:
            raise RuntimeError(f'Contagens divergentes: {parquet.name}')
        total += item['registros_parquet']
    if total != m.get('total_registros'):
        raise RuntimeError('Soma de registros divergente')
    return total


def executar_lote(codigo, competencia, lista_ufs, saida):
    fonte_compativel(codigo, [competencia])
    if not ROBO.is_file():
        raise FileNotFoundError(f'Robô original não localizado: {ROBO}')
    ufs = lista_ufs.split('-')
    if not ufs or len(ufs) > 3 or len(set(ufs)) != len(ufs) or any(u not in UF for u in ufs):
        raise ValueError('Lote inválido: use de 1 a 3 UFs distintas.')
    saida.mkdir(parents=True, exist_ok=True)
    status = []
    for uf in ufs:
        print(f'\n[EXTRACAO] {codigo} {uf} {competencia}', flush=True)
        antes = {p.name for p in saida.iterdir() if p.is_dir()}
        cmd = [sys.executable, str(ROBO), '--sistema', codigo.split('/')[0],
               '--subsistema', codigo.split('/')[1], '--uf', uf,
               '--competencia', competencia, '--saida', str(saida)]
        try:
            subprocess.run(cmd, check=True)
            novas = [p for p in saida.iterdir() if p.is_dir() and p.name not in antes]
            if len(novas) != 1:
                raise RuntimeError(f'Esperada uma pasta nova, encontradas {len(novas)}')
            linhas = conferir_saida(novas[0], codigo, uf, competencia)
            status.append(dict(uf=uf, competencia=competencia, status='sucesso', linhas=linhas, pasta=novas[0].name))
        except (OSError, subprocess.CalledProcessError, RuntimeError, KeyError, ValueError) as e:
            status.append(dict(uf=uf, competencia=competencia, status='erro', mensagem=str(e)))
            print(f'[ERRO] {uf} {competencia}: {e}', file=sys.stderr, flush=True)
    resumo = {'fonte': codigo, 'competencia': competencia, 'ufs': ufs, 'resultados': status}
    (saida / 'resumo_lote.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    total_ok = sum(s['status'] == 'sucesso' for s in status)
    print(f'[RESUMO] {total_ok}/{len(status)} UFs convertidas; saídas em {saida}', flush=True)
    if total_ok != len(status):
        raise RuntimeError(f'{len(status)-total_ok} UF(s) falharam. Inspecione resumo_lote.json e logs.')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fonte', required=True)
    p.add_argument('--competencia', required=True)
    p.add_argument('--matriz', action='store_true', help='Gera matriz JSON para distribuição dos lotes')
    p.add_argument('--ufs', help='Grupo de até 3 UFs separadas por hífen')
    p.add_argument('--saida', type=Path, default=Path('poc_dbc_online/saidas/real'))
    args = p.parse_args(argv)
    try:
        if args.matriz:
            resultado = matriz(args.fonte, args.competencia)
            print(json.dumps(resultado, separators=(',', ':')))
        else:
            if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', args.competencia):
                raise ValueError('Executor de lotes espera uma competência mensal; matriz expande anos.')
            if not args.ufs:
                raise ValueError('--ufs obrigatório para executar lote')
            executar_lote(args.fonte, args.competencia, args.ufs, args.saida)
        return 0
    except (ValueError, OSError, KeyError, RuntimeError, json.JSONDecodeError) as e:
        p.exit(2, f'ERRO: {e}\n')

if __name__ == '__main__':
    raise SystemExit(main())
