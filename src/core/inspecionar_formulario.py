import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_URL = "https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def"


class InspetorHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.formularios = []
        self.campos = []
        self.atual = None
        self.opcao = None

    def finalizar_opcao(self):
        if self.opcao is not None and self.atual is not None:
            self.opcao["texto"] = " ".join(
                self.opcao["texto"].split()
            )
            self.atual["opcoes"].append(self.opcao)
        self.opcao = None

    def finalizar_select(self):
        if self.atual is not None:
            self.finalizar_opcao()
            self.campos.append(self.atual)
            self.atual = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tag = tag.lower()

        if tag == "form":
            self.formularios.append({
                "method": a.get("method", "GET").upper(),
                "action": a.get("action", "")
            })

        elif tag == "select":
            self.finalizar_select()
            self.atual = {
                "id": a.get("id"),
                "name": a.get("name"),
                "multiple": "multiple" in a,
                "opcoes": []
            }

        elif tag == "option" and self.atual is not None:
            self.finalizar_opcao()
            self.opcao = {
                "value": a.get("value"),
                "texto": "",
                "selected": "selected" in a
            }

        elif tag == "input":
            if a.get("type", "text").lower() == "hidden":
                self.campos.append({
                    "tipo": "hidden",
                    "name": a.get("name"),
                    "value": a.get("value")
                })

    def handle_data(self, data):
        if self.opcao is not None:
            self.opcao["texto"] += data

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "option":
            self.finalizar_opcao()
        elif tag == "select":
            self.finalizar_select()

    def finalizar(self):
        self.finalizar_select()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    identificador = url.split("?")[-1].split("/")[-1].replace(".def", "")

    destino = Path("dados/inspecao")
    arquivo_saida = destino / (
        f"formulario_sia_{identificador}.json"
    )

    if arquivo_saida.exists():
        raise SystemExit(
            f"Inspecao existente preservada: {arquivo_saida}"
        )

    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0"
    })

    try:
        with urlopen(req, timeout=30) as resposta:
            html = resposta.read(5_000_000).decode(
                "iso-8859-1", errors="replace"
            )
    except Exception as erro:
        sys.exit(f"Erro ao acessar o TabNet: {erro}")

    parser = InspetorHTML()
    parser.feed(html)
    parser.finalizar()

    total_opcoes = sum(
        len(campo.get("opcoes", []))
        for campo in parser.campos
    )

    print(f"Formularios: {len(parser.formularios)}")
    print(f"Campos: {len(parser.campos)}")
    print(f"Total de opcoes: {total_opcoes}")

    for campo in parser.campos:
        if "opcoes" in campo:
            print(
                f"{str(campo['id']):18} "
                f"{len(campo['opcoes']):6} opcoes"
            )

    if not parser.formularios or total_opcoes == 0:
        sys.exit(
            "Formulario incompleto: nenhuma opcao identificada."
        )

    destino = Path("dados/inspecao")
    destino.mkdir(parents=True, exist_ok=True)

    resultado = {
        "url": url,
        "formularios": parser.formularios,
        "campos": parser.campos
    }

    arquivo = destino / f"formulario_sia_{identificador}.json"
    with arquivo.open("x", encoding="utf-8") as saida:
        json.dump(
            resultado,
            saida,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nResultado salvo em: {arquivo}")


if __name__ == "__main__":
    main()
