#!/usr/bin/env python3
"""Download real de DBCs do DATASUS em lotes com manifesto e SHA-256.

Mantém os arquivos DBC originais; não converte nem altera os dados.
Reutiliza a matriz e validação de fontes do script já integrado ao projeto.
"""
from __future__ import annotations
import argparse
import ftplib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import uuid

from extrair_parquet_actions import UF, ORIGINAL, fonte_compativel, matriz

HOST = 'ftp.datasus.gov.br'
MAX_ARQUIVO = 1024 * 1024 * 1024  # 1 GiB por DBC: proteção contra download inesperado
MAX_LOTE = 6 * 1024 * 1024 * 1024  # 6 GiB por job, proteção de disco


def selecionar(nomes, prefixo, uf, competencia):
    ano, mes = competencia.split('-')
    padrao = re.compile(rf'{re.escape(prefixo)}{uf}{ano[-2:]}{mes}[a-z]?\.dbc', re.I)
    return sorted({Path(n).name for n in nomes if padrao.fullmatch(Path(n).name)}, key=str.casefold)


def sha256(caminho):
    h = hashlib.sha256()
    with caminho.open('rb') as arq:
        for bloco in iter(lambda: arq.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def baixar(ftp, nome, destino, limite=MAX_ARQUIVO):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.dbc', nome, re.I) or Path(nome).name != nome:
        raise ValueError('Nome remoto não permitido')
    ftp.voidcmd('TYPE I')
    tamanho_remoto = ftp.size(nome)
    if tamanho_remoto is not None and tamanho_remoto > limite:
        raise ValueError(f'{nome}: tamanho remoto excede 1 GiB')
    parcial = destino.with_suffix(destino.suffix + '.part')
    total = 0
    digest = hashlib.sha256()
    try:
        with parcial.open('wb') as arq:
            def escrever(bloco):
                nonlocal total
                total += len(bloco)
                if total > limite:
                    raise ValueError(f'{nome}: limite de transferência excedido')
                arq.write(bloco)
                digest.update(bloco)
            ftp.retrbinary('RETR ' + nome, escrever, blocksize=256 * 1024)
        if total == 0 or (tamanho_remoto is not None and total != tamanho_remoto):
            raise IOError(f'{nome}: download vazio ou incompleto ({total} de {tamanho_remoto} bytes)')
        parcial.replace(destino)
        return {'arquivo': nome, 'bytes_dbc': total, 'sha256_dbc': digest.hexdigest()}
    finally:
        parcial.unlink(missing_ok=True)


def executar(codigo, competencia, ufs_texto, raiz):
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', competencia):
        raise ValueError('Informe competência mensal AAAA-MM; anos são expandidos pela matriz')
    fonte_compativel(codigo, [competencia])
    ufs = ufs_texto.split('-')
    if not 1 <= len(ufs) <= 3 or len(set(ufs)) != len(ufs) or any(uf not in UF for uf in ufs):
        raise ValueError('Informe de 1 a 3 UFs distintas, separadas por hífen')
    sistema, subsistema = codigo.split('/')
    originais = json.loads(ORIGINAL.read_text(encoding='utf-8'))['fontes']
    reg = next(f for f in originais if f['sistema'] == sistema and f['subsistema'] == subsistema)
    diretorio = reg['diretorio_ftp']
    prefixo = reg['prefixo']
    runid = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    destino = raiz / f'{sistema.lower()}_{subsistema.lower()}_{competencia}_{"-".join(ufs).lower()}_{runid}'
    destino.mkdir(parents=True, exist_ok=False)
    manifestos = []
    erros = []
    ftp = ftplib.FTP(timeout=60)
    try:
        ftp.connect(HOST, 21)
        ftp.login('anonymous', 'anonymous@')
        ftp.set_pasv(True)
        ftp.cwd(diretorio)
        nomes = [Path(n).name for n in ftp.nlst()]
        print(f'[FTP] {HOST}{diretorio}: {len(nomes)} nomes listados', flush=True)
        bytes_lote = 0
        for uf in ufs:
            arquivos = selecionar(nomes, prefixo, uf, competencia)
            if not arquivos:
                erros.append(f'{uf}: nenhum DBC correspondente')
                print('[ERRO]', erros[-1], file=sys.stderr)
                continue
            pasta = destino / uf
            pasta.mkdir()
            itens = []
            for nome in arquivos:
                try:
                    print(f'[DOWNLOAD] {uf}: {nome}', flush=True)
                    item = baixar(ftp, nome, pasta / nome)
                    bytes_lote += item['bytes_dbc']
                    if bytes_lote > MAX_LOTE:
                        raise ValueError('Lote excedeu 6 GiB; reduza UFs por job')
                    itens.append(item)
                except (OSError, ValueError) + ftplib.all_errors as exc:
                    erros.append(f'{uf}/{nome}: {exc}')
                    print('[ERRO]', erros[-1], file=sys.stderr)
            if itens:
                m = {'fonte': codigo, 'uf': uf, 'competencia': competencia,
                     'origem': f'ftp://{HOST}{diretorio}/',
                     'download_em_utc': datetime.now(timezone.utc).isoformat(),
                     'formato': 'DBC original (sem conversão)',
                     'arquivos': itens}
                (pasta / 'manifesto.json').write_text(json.dumps(m, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
                manifestos.append(m)
    finally:
        try:
            ftp.quit()
        except (OSError, EOFError) + ftplib.all_errors:
            ftp.close()
    resumo = {'fonte': codigo, 'competencia': competencia, 'ufs_solicitadas': ufs,
              'ufs_com_download': [m['uf'] for m in manifestos], 'erros': erros,
              'quantidade_dbc': sum(len(m['arquivos']) for m in manifestos)}
    (destino / 'resumo_lote.json').write_text(json.dumps(resumo, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('[RESUMO]', json.dumps(resumo, ensure_ascii=False), flush=True)
    if erros or len(manifestos) != len(ufs):
        raise RuntimeError(f'Falha em {len(erros)} arquivo(s)/UF(s); confira resumo_lote.json')
    return destino


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fonte', required=True)
    ap.add_argument('--competencia', required=True)
    ap.add_argument('--matriz', action='store_true')
    ap.add_argument('--ufs')
    ap.add_argument('--saida', type=Path, default=Path('poc_dbc_online/saidas/dbc'))
    args = ap.parse_args(argv)
    try:
        if args.matriz:
            print(json.dumps(matriz(args.fonte, args.competencia), separators=(',', ':')))
        else:
            if not args.ufs:
                raise ValueError('Faltou informar --ufs')
            executar(args.fonte, args.competencia, args.ufs, args.saida)
        return 0
    except (ValueError, OSError, RuntimeError) + ftplib.all_errors as exc:
        ap.exit(2, f'ERRO: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
