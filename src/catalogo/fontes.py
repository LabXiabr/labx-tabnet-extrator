"""Cadastro validado de fontes; nao executa consultas de rede."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / "configuracoes" / "fontes"
CODIGO = re.compile(r"[A-Z][A-Z0-9_]{1,19}\Z")
ID = re.compile(r"[a-z][a-z0-9_]{2,79}\Z")


@dataclass(frozen=True)
class Fonte:
    id: str
    sistema: str
    subsistema: str
    descricao: str
    status: str
    url_formulario: str | None
    granularidade: str
    indicadores: tuple[str, ...]
    dimensoes: tuple[str, ...]
    observacoes: str
    arquivo: Path

    @property
    def homologada(self) -> bool:
        return self.status == "homologada"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sistema": self.sistema,
            "subsistema": self.subsistema,
            "descricao": self.descricao,
            "status": self.status,
            "url_formulario": self.url_formulario,
            "granularidade": self.granularidade,
            "indicadores": list(self.indicadores),
            "dimensoes": list(self.dimensoes),
            "observacoes": self.observacoes,
        }


def carregar_fonte(caminho: Path) -> Fonte:
    caminho = Path(caminho)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError(f"{caminho}: documento deve ser objeto JSON")
    obrigatorios = {"id", "sistema", "subsistema", "descricao", "status", "granularidade", "indicadores", "dimensoes", "observacoes", "url_formulario"}
    extras = set(dados) - obrigatorios
    faltantes = obrigatorios - set(dados)
    if extras or faltantes:
        raise ValueError(f"{caminho}: campos faltantes={sorted(faltantes)} extras={sorted(extras)}")
    for campo, padrao in (("id", ID), ("sistema", CODIGO), ("subsistema", CODIGO)):
        valor = dados[campo]
        if not isinstance(valor, str) or not padrao.fullmatch(valor):
            raise ValueError(f"{caminho}: {campo} invalido")
    if dados["id"] != f'{dados["sistema"]}_{dados["subsistema"]}'.lower():
        raise ValueError(f"{caminho}: id deve corresponder a sistema/subsistema")
    if dados["status"] not in ("homologada", "planejada", "em_validacao"):
        raise ValueError(f"{caminho}: status invalido")
    for campo in ("descricao", "granularidade", "observacoes"):
        if not isinstance(dados[campo], str) or (campo != "observacoes" and not dados[campo].strip()):
            raise ValueError(f"{caminho}: {campo} invalido")
    for campo in ("indicadores", "dimensoes"):
        valores = dados[campo]
        if not isinstance(valores, list) or not all(isinstance(x, str) and x.strip() for x in valores) or len(set(valores)) != len(valores):
            raise ValueError(f"{caminho}: {campo} invalido ou duplicado")
    url = dados["url_formulario"]
    if url is not None and (not isinstance(url, str) or not url.startswith(("http://tabnet.datasus.gov.br/", "https://tabnet.datasus.gov.br/"))):
        raise ValueError(f"{caminho}: URL deve ser do TabNet DATASUS")
    if dados["status"] == "homologada" and (not url or not dados["indicadores"] or not dados["dimensoes"]):
        raise ValueError(f"{caminho}: fonte homologada requer URL, indicadores e dimensoes")
    return Fonte(arquivo=caminho, **{**dados, "indicadores": tuple(dados["indicadores"]), "dimensoes": tuple(dados["dimensoes"])})


def listar_fontes(pasta: Path = PASTA_PADRAO) -> list[Fonte]:
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise FileNotFoundError(f"Catalogo inexistente: {pasta}")
    fontes = [carregar_fonte(arquivo) for arquivo in sorted(pasta.glob("*.json"))]
    if not fontes:
        raise ValueError(f"Catalogo sem fontes: {pasta}")
    ids = [f.id for f in fontes]
    if len(ids) != len(set(ids)):
        raise ValueError("Fontes com IDs duplicados")
    return fontes


def obter_fonte(sistema: str, subsistema: str, pasta: Path = PASTA_PADRAO, *, exigir_homologada: bool = True) -> Fonte:
    encontrados = [f for f in listar_fontes(pasta) if f.sistema == sistema.upper() and f.subsistema == subsistema.upper()]
    if not encontrados:
        raise ValueError(f"Fonte {sistema}/{subsistema} nao cadastrada")
    fonte = encontrados[0]
    if exigir_homologada and not fonte.homologada:
        raise ValueError(f"Fonte {sistema}/{subsistema} ainda nao homologada: {fonte.status}")
    return fonte
