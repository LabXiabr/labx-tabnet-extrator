"""Executa consulta nova ao FTP oficial e converte arquivos DBC em Parquet.

CLI: python -m poc_dbc_online.robo --sistema SIA --subsistema PA --uf AC --competencia 2009-04
Sem historico/caches. Nao usa codigo existente nem modifica dados do repositorio.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import ftplib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

FTP_HOST = "ftp.datasus.gov.br"
CATALOGO = Path(__file__).with_name("fontes.json")
UF_VALIDAS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


def catalogo():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))["fontes"]


def obter_fonte(sistema: str, subsistema: str):
    for f in catalogo():
        if f["sistema"] == sistema.upper() and f["subsistema"] == subsistema.upper():
            if f["status"] == "planejada" or not f["diretorio_ftp"]:
                raise ValueError(f"Fonte {sistema}/{subsistema} ainda nao configurada para DBC real")
            return f
    raise ValueError(f"Fonte desconhecida: {sistema}/{subsistema}")


def validar_entrada(fonte, uf, competencia):
    uf = uf.upper()
    if uf not in UF_VALIDAS:
        raise ValueError("UF invalida")
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", competencia):
        raise ValueError("Competencia invalida; use AAAA-MM, de 2000 em diante")
    if competencia < fonte["inicio"]:
        raise ValueError(f"Competencia anterior ao inicio catalogado ({fonte['inicio']})")
    if competencia > datetime.now(timezone.utc).strftime("%Y-%m"):
        raise ValueError("Competencia futura")
    return uf


def nome_arquivo(fonte, uf, competencia):
    """Aceita sufixo de particao (a, b ...) e extensao com caixa variada."""
    ano, mes = competencia.split("-")
    return re.compile(
        rf"^{re.escape(fonte['prefixo'])}{uf}{ano[-2:]}{mes}[a-z]?\.dbc$",
        re.IGNORECASE,
    )


def abrir_ftp():
    ftp = ftplib.FTP(timeout=45)
    ftp.connect(FTP_HOST, 21)
    ftp.login("anonymous", "anonymous@")
    ftp.set_pasv(True)
    return ftp


def listar_arquivos(ftp, diretorio):
    """Executa NLST remoto a cada rodada; nao depende de inventario local."""
    ftp.cwd(diretorio)
    return [Path(n).name for n in ftp.nlst()]


def selecionar_arquivos(nomes, fonte, uf, competencia):
    padrao = nome_arquivo(fonte, uf, competencia)
    achados = sorted({n for n in nomes if padrao.fullmatch(Path(n).name)}, key=str.casefold)
    if not achados:
        raise FileNotFoundError(
            f"Nenhum DBC encontrado para {fonte['sistema']}/{fonte['subsistema']} "
            f"{uf} {competencia} no diretorio configurado"
        )
    return achados


def hash_arquivo(path):
    h = hashlib.sha256()
    with open(path, "rb") as arq:
        for bloco in iter(lambda: arq.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(ftp, nome, destino, max_bytes):
    """Sempre faz RETR novo; grava em .part; valida tamanho antes de promover."""
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.dbc", nome, re.IGNORECASE):
        raise ValueError("Nome remoto inseguro")
    tamanho = ftp.size(nome)
    if tamanho is not None and tamanho > max_bytes:
        raise ValueError(f"DBC de {tamanho} bytes excede limite de {max_bytes} bytes da PoC")
    contador = 0
    parcial = destino.with_name(destino.name + ".part")
    try:
        with open(parcial, "wb") as arq:
            def escrever(bloco):
                nonlocal contador
                contador += len(bloco)
                if contador > max_bytes:
                    raise ValueError("Download excedeu limite da PoC")
                arq.write(bloco)
            ftp.retrbinary(f"RETR {nome}", escrever, blocksize=256 * 1024)
        if contador == 0 or (tamanho is not None and contador != tamanho):
            raise IOError(f"Download incompleto: {contador} bytes; esperado {tamanho}")
        parcial.rename(destino)
    finally:
        parcial.unlink(missing_ok=True)
    return contador


def dbc_para_dbf(dbc, dbf):
    """Conversor externo auditavel; sem copia de codigo de terceiros."""
    subprocess.run([sys.executable, "-m", "dbctodbf", str(dbc), str(dbf)], check=True, timeout=600)
    if not dbf.is_file() or dbf.stat().st_size < 32:
        raise RuntimeError("Conversor nao produziu DBF valido")


def dbf_para_csv(dbf, csv_saida):
    """Streaming para evitar materializar todo DBF em RAM; valores de origem como texto."""
    try:
        from dbfread import DBF
    except ImportError as e:
        raise RuntimeError("Instale as dependencias da PoC com pip") from e
    tabela = DBF(str(dbf), encoding="latin1", char_decode_errors="strict", load=False,
                 ignore_missing_memofile=True)
    campos = tabela.field_names
    if not campos:
        raise ValueError("DBF sem colunas")
    contador = 0
    with open(csv_saida, "w", newline="", encoding="utf-8") as arq:
        escritor = csv.writer(arq)
        escritor.writerow(campos)
        for linha in tabela:
            escritor.writerow(["" if linha[c] is None else str(linha[c]) for c in campos])
            contador += 1
    return contador, campos


def csv_para_parquet(csv_entrada, parquet_saida):
    """DuckDB faz a escrita final Parquet. Evita inferencia de inteiros em IDs/codigos."""
    try:
        import duckdb
    except ImportError as e:
        raise RuntimeError("Instale duckdb antes da conversao") from e
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("SET threads=2")
        con.execute("CREATE TABLE dados AS SELECT * FROM read_csv(?, header=true, all_varchar=true)",
                    [str(csv_entrada)])
        rows = con.execute("SELECT count(*) FROM dados").fetchone()[0]
        # Caminhos sao locais e controlados, com escape de aspas em SQL.
        destino_sql = "'" + str(parquet_saida).replace("'", "''") + "'"
        con.execute(f"COPY dados TO {destino_sql} (FORMAT parquet, COMPRESSION zstd)")
        confirmar = con.execute("SELECT count(*) FROM read_parquet(?)", [str(parquet_saida)]).fetchone()[0]
        if rows != confirmar:
            raise RuntimeError("Divergencia de contagem no Parquet")
        return rows
    finally:
        con.close()


def executar(sistema, subsistema, uf, competencia, saida, max_mb=80):
    fonte = obter_fonte(sistema, subsistema)
    uf = validar_entrada(fonte, uf, competencia)
    if max_mb < 1 or max_mb > 500:
        raise ValueError("Limite da PoC deve estar entre 1 e 500 MB")
    saida = Path(saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    execucao_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    pasta_final = saida / f"{fonte['sistema'].lower()}_{fonte['subsistema'].lower()}_{uf.lower()}_{competencia}_{execucao_id}"
    pasta_final.mkdir()
    inicio = datetime.now(timezone.utc).isoformat()
    try:
        ftp = abrir_ftp()
        try:
            ftp.cwd(fonte["diretorio_ftp"])
            nomes = listar_arquivos(ftp, fonte["diretorio_ftp"])
            selecionados = selecionar_arquivos(nomes, fonte, uf, competencia)
            print("Arquivos oficiais encontrados:", ", ".join(selecionados), flush=True)
            if len(selecionados) > 6:
                raise RuntimeError("Mais de 6 particoes; revise a descoberta manualmente")
            registros_totais = 0
            inventario = []
            with tempfile.TemporaryDirectory(prefix="labx-dbc-") as td:
                temp = Path(td)
                for nome in selecionados:
                    dbc = temp / nome
                    dbf = temp / (Path(nome).stem + ".dbf")
                    intermediario = temp / (Path(nome).stem + ".csv")
                    saida_parquet = pasta_final / (Path(nome).stem.lower() + ".parquet")
                    print("Baixando:", nome, flush=True)
                    bytes_baixados = baixar(ftp, nome, dbc, max_mb * 1024 * 1024)
                    digest = hash_arquivo(dbc)
                    print("Convertendo DBC/DBF/Parquet:", nome, flush=True)
                    dbc_para_dbf(dbc, dbf)
                    linhas_dbf, campos = dbf_para_csv(dbf, intermediario)
                    linhas_parquet = csv_para_parquet(intermediario, saida_parquet)
                    if linhas_dbf != linhas_parquet:
                        raise RuntimeError(f"Contagem divergente em {nome}")
                    registros_totais += linhas_parquet
                    inventario.append({
                        "arquivo": nome,
                        "url_origem": f"ftp://{FTP_HOST}{fonte['diretorio_ftp']}/{nome}",
                        "bytes_dbc": bytes_baixados,
                        "sha256_dbc": digest,
                        "colunas": campos,
                        "registros_dbf": linhas_dbf,
                        "registros_parquet": linhas_parquet,
                        "parquet": saida_parquet.name,
                        "sha256_parquet": hash_arquivo(saida_parquet),
                    })
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()
        manifesto = {
            "id": execucao_id, "status": "convertido_nao_homologado",
            "sistema": fonte["sistema"], "subsistema": fonte["subsistema"],
            "uf": uf, "competencia": competencia,
            "consultado_em_utc": inicio,
            "fonte": f"ftp://{FTP_HOST}{fonte['diretorio_ftp']}",
            "modo": "download_novo_sem_cache",
            "total_registros": registros_totais,
            "validacoes": ["tamanho_download", "sha256_dbc", "contagem_dbf_parquet", "sha256_parquet"],
            "pendencias": ["tipagem_semantica", "comparacao_tabnet", "equivalencia_etl_felipe"],
            "arquivos": inventario,
        }
        (pasta_final / "manifesto.json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"CONCLUIDO: {pasta_final} | registros={registros_totais}", flush=True)
        return pasta_final
    except Exception:
        # Evita deixar diretorio parcial interpretavel como execucao concluida.
        shutil.rmtree(pasta_final, ignore_errors=True)
        raise


def main():
    p = argparse.ArgumentParser(description="PoC: consulta nova ao DATASUS e converte DBC em Parquet")
    p.add_argument("--sistema", required=True)
    p.add_argument("--subsistema", required=True)
    p.add_argument("--uf", required=True)
    p.add_argument("--competencia", required=True)
    p.add_argument("--saida", default="poc_dbc_online/saidas")
    p.add_argument("--max-mb", type=int, default=80)
    args = p.parse_args()
    try:
        executar(args.sistema.upper(), args.subsistema.upper(), args.uf.upper(),
                 args.competencia, args.saida, args.max_mb)
    except Exception as e:
        print(f"ERRO: {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
