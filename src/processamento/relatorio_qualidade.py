import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from normalizar_tabnet import (
    UFS_VALIDAS,
    extrair_registros,
)


def construir_relatorio(html, competencia, grupo):
    # Reutiliza todas as validacoes do normalizador.
    registros, total_informado = extrair_registros(
        html, competencia, grupo
    )

    presentes = {r["sg_uf"] for r in registros}
    ausentes = sorted(UFS_VALIDAS - presentes)
    total_calculado = sum(
        r["qt_aprovada"] for r in registros
    )

    return {
        "sistema": "SIA",
        "subsistema": "AM",
        "formulario": "sia/cnv/qabr.def",
        "competencia": competencia,
        "grupo_procedimento": grupo,
        "ufs_presentes": len(presentes),
        "ufs_ausentes": ausentes,
        "total_informado": total_informado,
        "total_calculado": total_calculado,
        "total_consistente": (
            total_informado == total_calculado
        ),
        "status": (
            "validado_com_ausencias"
            if ausentes else "validado"
        ),
        "observacoes": (
            ["UFs ausentes nao foram convertidas em zero."]
            if ausentes else []
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Relatorio de qualidade SIA/AM"
    )
    parser.add_argument("--entrada", required=True)
    parser.add_argument("--saida", required=True)
    parser.add_argument("--competencia", required=True)
    parser.add_argument("--grupo", default="6")

    args = parser.parse_args()

    entrada = Path(args.entrada)
    saida = Path(args.saida)

    html = entrada.read_bytes().decode(
        "iso-8859-1", errors="replace"
    )

    relatorio = construir_relatorio(
        html, args.competencia, args.grupo
    )

    relatorio["arquivo_origem"] = str(entrada)
    relatorio["gerado_em_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    saida.parent.mkdir(parents=True, exist_ok=True)

    saida.write_text(
        json.dumps(
            relatorio,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print("RELATORIO DE QUALIDADE GERADO")
    print("Competencia:", args.competencia)
    print("UFs presentes:", relatorio["ufs_presentes"])
    print("UFs ausentes:", relatorio["ufs_ausentes"])
    print("Total:", relatorio["total_informado"])
    print("Status:", relatorio["status"])
    print("Arquivo:", saida)


if __name__ == "__main__":
    main()
