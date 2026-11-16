import csv
import json
from pathlib import Path

from core.caminhos import nome_execucao


UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF",
    "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
    "RO", "RR", "SC", "SP", "SE", "TO",
}


def verificar_competencia(competencia, raiz):
    identificador = nome_execucao(
        "SIA", "AM", competencia
    )
    pasta = Path(raiz) / "dados/execucoes" / identificador

    csv_arquivo = pasta / "normalizado.csv"
    qualidade = pasta / "qualidade.json"
    validacao = pasta / "validacao_cruzada.json"

    if not all(
        arquivo.is_file()
        for arquivo in (csv_arquivo, qualidade, validacao)
    ):
        return False

    try:
        cruzada = json.loads(
            validacao.read_text(encoding="utf-8")
        )
        relatorio = json.loads(
            qualidade.read_text(encoding="utf-8")
        )

        if (
            cruzada.get("competencia") != competencia
            or cruzada.get("status") != "aprovado"
            or cruzada.get("divergencias") != []
            or relatorio.get("competencia") != competencia
            or relatorio.get("sistema") != "SIA"
            or relatorio.get("subsistema") != "AM"
            or str(relatorio.get("grupo_procedimento")) != "6"
            or relatorio.get("total_consistente") is not True
            or relatorio.get("status") not in (
                "validado", "validado_com_ausencias"
            )
        ):
            return False

        with csv_arquivo.open(
            encoding="utf-8", newline=""
        ) as arquivo:
            leitor = csv.DictReader(arquivo)

            if leitor.fieldnames != [
                "sg_uf", "dt_competencia", "qt_aprovada"
            ]:
                return False

            registros = list(leitor)

        if not registros:
            return False

        ufs = set()
        total = 0

        for registro in registros:
            uf = registro["sg_uf"]
            data = registro["dt_competencia"]
            quantidade = registro["qt_aprovada"]

            if (
                uf not in UFS_VALIDAS
                or uf in ufs
                or data != competencia + "-01"
                or not isinstance(quantidade, str)
                or not quantidade.isascii()
                or not quantidade.isdecimal()
            ):
                return False

            ufs.add(uf)
            total += int(quantidade)

        ausentes = UFS_VALIDAS - ufs

        return (
            len(ufs) == cruzada.get("ufs_extraidas")
            and len(ufs) == cruzada.get("ufs_oficial")
            and len(ufs) == relatorio.get("ufs_presentes")
            and set(relatorio.get("ufs_ausentes", [])) == ausentes
            and set(
                cruzada.get("ufs_ausentes_na_fonte", [])
            ) == ausentes
            and total == cruzada.get("total_extraido")
            and total == cruzada.get("total_oficial")
            and total == relatorio.get("total_calculado")
            and total == relatorio.get("total_informado")
        )

    except (
        OSError, ValueError, KeyError, TypeError,
        UnicodeError, csv.Error
    ):
        return False

