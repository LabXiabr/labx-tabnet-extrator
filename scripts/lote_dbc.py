#!/usr/bin/env python3
"""Descoberta de DBC no FTP da planilha e despacho para o robô existente.
Não implementa conversão: preserva o robô já validado do projeto.
"""
import argparse
import ftplib
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

UF = set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
ROOT = Path(__file__).resolve().parents[1]
CATALOGO = ROOT / 'catalogo' / 'fontes_sus.json'
CATALOGO_ROBO = ROOT / 'poc_dbc_online' / 'fontes.json'
LIMITE_EXECUCAO = 27


def competencias(texto):
    if re.fullmatch(r'\d{4}', texto):
        ano = int(texto)
        if not 1990 <= ano <= date.today().year: raise ValueError('Ano fora do intervalo aceito')
        return [f'{ano}-{mes:02d}' for mes in range(1, 13)]
    try:
        ano, mes = map(int, texto.split('-'))
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', texto) or not 1990 <= ano <= date.today().year:
            raise ValueError()
        return [texto]
    except (ValueError, AttributeError):
        raise ValueError('Competência deve ser AAAA ou AAAA-MM') from None


def fonte(catalogo, codigo):
    if not re.fullmatch(r'[A-Z0-9_]+/[A-Z0-9_]+', codigo):
        raise ValueError('Fonte inválida')
    try: registro = catalogo['fontes'][codigo]
    except KeyError: raise ValueError(f'Fonte não cadastrada: {codigo}') from None
    if registro['revisao_necessaria']:
        raise ValueError(f'{codigo} precisa de revisão de diretórios/prefixos antes de executar')
    if not registro['diretorios']:
        raise ValueError(f'{codigo} cadastrada, porém sem diretório de dados na planilha')
    return registro


def urls_para_competencia(registro, comp):
    valor = int(comp.replace('-', ''))
    urls = []
    for item in registro['diretorios']:
        url = item['url']
        janelas = re.findall(r'(\d{6})_(\d{6})?', url)
        if janelas:
            ini, fim = janelas[-1]
            if valor < int(ini) or (fim and valor > int(fim)):
                continue
        urls.append(url)
    return list(dict.fromkeys(urls))


def arquivos_ftp(url, timeout=25):
    parsed = urlsplit(url)
    if parsed.scheme != 'ftp' or parsed.hostname != 'ftp.datasus.gov.br':
        raise ValueError('Apenas FTP oficial cadastrado é permitido')
    ftp = ftplib.FTP(timeout=timeout)
    try:
        ftp.connect(parsed.hostname, parsed.port or 21)
        ftp.login()
        ftp.cwd(parsed.path)
        return [s.rsplit('/', 1)[-1] for s in ftp.nlst()]
    finally:
        try: ftp.quit()
        except (OSError, EOFError, ftplib.Error):
            ftp.close()


def filtrar_arquivos(nomes, prefixo, competencia):
    """Layout padrão e partições opcionais a-z; padrões não estaduais ficam pendentes."""
    a, m = competencia.split('-')
    pat = re.compile(rf'^{re.escape(prefixo)}(?P<uf>[A-Z]{{2}}){a[-2:]}{m}[a-z]?\.dbc$', re.IGNORECASE)
    itens = []
    for nome in nomes:
        encontrado = pat.fullmatch(nome)
        if encontrado and encontrado.group('uf').upper() in UF:
            itens.append((encontrado.group('uf').upper(), nome))
    return sorted(set(itens))


def descobrir(registro, codigo, comp, listar=arquivos_ftp):
    achados = []
    for url in urls_para_competencia(registro, comp):
        nomes = listar(url)
        correspondentes = filtrar_arquivos(nomes, registro['subsistema'], comp)
        print(f"[FTP] {codigo} {comp}: {len(nomes)} nomes listados; "
              f"{len(correspondentes)} arquivos correspondentes; diretorio={url}", flush=True)
        if not correspondentes:
            amostra = ', '.join(sorted(nomes)[:5]) if nomes else '(listagem vazia)'
            print(f"[FTP] Amostra da listagem: {amostra}", flush=True)
        for uf, nome in correspondentes:
            achados.append(dict(fonte=codigo, competencia=comp, uf=uf, arquivo=nome, url_diretorio=url))
    chave = lambda d: (d['competencia'], d['uf'], d['arquivo'], d['url_diretorio'])
    return sorted({tuple(sorted(a.items())):a for a in achados}.values(), key=chave)


def verificar_compatibilidade_robo(codigo, registro, comps, plano, caminho_catalogo=CATALOGO_ROBO):
    """Falha fechada: só executa fonte suportada pela configuração original do robô."""
    if not caminho_catalogo.is_file():
        raise ValueError(f'Catálogo do robô original não encontrado: {caminho_catalogo}')
    fontes = json.loads(caminho_catalogo.read_text(encoding='utf-8')).get('fontes', [])
    if not isinstance(fontes, list):
        raise ValueError('Catálogo original incompatível: fontes não é uma lista')
    originais = [f for f in fontes if f.get('sistema') == registro['sistema']
                 and f.get('subsistema') == registro['subsistema']]
    if len(originais) != 1:
        raise ValueError(f'{codigo}: apenas descoberta habilitada; fonte não configurada no robô original')
    original = originais[0]
    if original.get('status') == 'planejada' or not original.get('diretorio_ftp'):
        raise ValueError(f'{codigo}: fonte ainda não habilitada para conversão no robô original')
    if original.get('prefixo', '').upper() != registro['subsistema'].upper():
        raise ValueError(f'{codigo}: prefixos divergentes entre os catálogos')
    esperado = original['diretorio_ftp'].rstrip('/')
    for item in plano:
        diretorio = urlsplit(item['url_diretorio']).path.rstrip('/')
        if diretorio != esperado:
            raise ValueError(f'{codigo}: diretório novo incompatível com o robô: {diretorio}')
    inicio = original.get('inicio')
    atual = datetime.now(timezone.utc).strftime('%Y-%m')
    for comp in comps:
        if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', comp):
            raise ValueError(f'{codigo}: robô original aceita somente competências a partir de 2000')
        if inicio and comp < inicio:
            raise ValueError(f'{codigo}: {comp} anterior ao início permitido {inicio}')
        if comp > atual:
            raise ValueError(f'{codigo}: competência futura {comp}')
    # O robô processa uma UF/competência e busca todas suas partições.
    # Impedir chamadas repetidas para a mesma UF/competência.
    grupos = {(item['uf'], item['competencia']) for item in plano}
    if len(grupos) > LIMITE_EXECUCAO:
        raise ValueError(f'Execução bloqueada: {len(grupos)} grupos; máximo da primeira entrega: {LIMITE_EXECUCAO}')
    return sorted(grupos, key=lambda g: (g[1], g[0]))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fonte',required=True,help='Ex.: SIA/PA')
    p.add_argument('--competencia',required=True,help='AAAA ou AAAA-MM')
    p.add_argument('--catalogo',type=Path,default=CATALOGO)
    p.add_argument('--saida-plano',type=Path,default=Path('poc_dbc_online/saidas/plano_lote.json'))
    p.add_argument('--executar',action='store_true',help='Despacha cada arquivo para o robô existente')
    p.add_argument('--robo',type=Path,default=Path('poc_dbc_online/robo.py'))
    p.add_argument('--max-arquivos',type=int,default=0,help='0 = sem limite na descoberta; execução limitada a 27 grupos')
    args = p.parse_args(argv)
    try:
        catalogo=json.loads(args.catalogo.read_text(encoding='utf-8'))
        reg=fonte(catalogo,args.fonte)
        comps=competencias(args.competencia)
        print(f"[PARAMETROS] fonte={args.fonte} competencia={args.competencia} "
              f"modo={'executar' if args.executar else 'planejar'}", flush=True)
        plano=[]
        for c in comps:
            plano.extend(descobrir(reg,args.fonte,c))
        if args.max_arquivos < 0: raise ValueError('max-arquivos deve ser >= 0')
        if args.max_arquivos and len(plano)>args.max_arquivos:
            raise ValueError(f'Encontrados {len(plano)} arquivos; limite é {args.max_arquivos}; nenhuma execução realizada')
        grupos_execucao = verificar_compatibilidade_robo(args.fonte, reg, comps, plano) if args.executar and plano else []
        data={'fonte':args.fonte,'competencias':comps,'arquivos':plano,'quantidade':len(plano),'modo':'executar' if args.executar else 'planejar',
              'nota':'Descoberta ao vivo no FTP; padrão PREF+UF+AAMM com partição opcional. Disponibilidade não garante homologação.'}
        args.saida_plano.parent.mkdir(parents=True,exist_ok=True)
        args.saida_plano.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'Encontrados {len(plano)} arquivos; plano em {args.saida_plano}')
        if not plano: raise ValueError('Nenhum DBC encontrado. Verifique padrão do nome e caminho FTP; não considerar extração concluída')
        if args.executar:
            if not args.robo.is_file(): raise ValueError(f'Robô não encontrado: {args.robo}')
            for i,(uf,comp) in enumerate(grupos_execucao,1):
                cmd=[sys.executable,str(args.robo),'--sistema',reg['sistema'],'--subsistema',reg['subsistema'],'--uf',uf,'--competencia',comp]
                print(f'[{i}/{len(grupos_execucao)}] {args.fonte} {uf} {comp}',flush=True)
                subprocess.run(cmd,check=True)
    except (ValueError, OSError, EOFError, ftplib.Error, subprocess.CalledProcessError) as exc:
        p.exit(2,f'ERRO: {exc}\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
