import hashlib
import json
from pathlib import Path

from datetime import datetime, timezone


def gerar_manifesto_competencia(
    raiz, sistema, subsistema, competencia
):
    raiz = Path(raiz)

    identificador = (
        f"{sistema.lower()}_{subsistema.lower()}_"
        f"{competencia.replace('-', '')}"
    )

    pasta = raiz / "dados/execucoes" / identificador
    html = raiz / "dados/respostas" / f"{identificador}.html"

    arquivos = [
        html,
        pasta / "normalizado.csv",
        pasta / "qualidade.json",
        pasta / "validacao_cruzada.json",
        pasta / "oficial.csv",
    ]

    for arquivo in arquivos:
        if not arquivo.is_file():
            raise FileNotFoundError(
                f"Arquivo obrigatorio ausente: {arquivo}"
            )

    registros = []

    for arquivo in arquivos:
        conteudo = arquivo.read_bytes()

        registros.append({
            "caminho": str(arquivo.relative_to(raiz)),
            "tamanho_bytes": len(conteudo),
            "sha256": hashlib.sha256(
                conteudo
            ).hexdigest(),
        })

    manifesto = {
        "versao": 1,
        "sistema": sistema.upper(),
        "subsistema": subsistema.upper(),
        "competencia": competencia,
        "gerado_em_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_arquivos": len(registros),
        "arquivos": registros,
    }

    destino = (
        raiz / "dados/auditoria"
        / f"{identificador}_manifesto.json"
    )

    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        raise FileExistsError(
            f"Manifesto ja existe: {destino}"
        )

    destino.write_text(
        json.dumps(
            manifesto, ensure_ascii=False, indent=2
        ) + "\n",
        encoding="utf-8",
    )

    return destino
