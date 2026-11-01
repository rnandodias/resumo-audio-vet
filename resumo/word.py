"""Conversão dos materiais de Markdown para Word e conferência do arquivo gerado contra o Markdown."""

import json
import logging
from pathlib import Path

import pypandoc
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE

log = logging.getLogger(__name__)

# Estilos do Word (tabelas com grade e cabeçalho em negrito, fonte, idioma pt-BR), feitos a partir do
# reference.docx padrão do pandoc; para mudar o visual, edite os estilos desse arquivo no próprio Word.
REFERENCIA = Path(__file__).with_name("referencia.docx")
# O modelo costuma abrir uma lista logo abaixo do parágrafo, sem linha em branco; sem a extensão, os itens
# viram texto corrido dentro do parágrafo ("... autoimune. - O ataque ...").
FORMATO = "markdown+lists_without_preceding_blankline"


def converter(markdown: Path, destino: Path, sumario: bool) -> dict:
    extras = ["--reference-doc", str(REFERENCIA)] + (["--toc", "--toc-depth=3"] if sumario else [])
    pypandoc.convert_file(str(markdown), "docx", format=FORMATO, outputfile=str(destino), extra_args=extras)
    return conferir(markdown, destino)


def _estrutura(markdown: Path) -> tuple[int, int, set[str]]:
    """Títulos de nível 1, tabelas e URLs externas do Markdown, lidos pelo AST do pandoc."""
    contagem, urls = {"nivel_1": 0, "tabelas": 0}, set()

    def percorrer(no):
        if isinstance(no, dict):
            if no.get("t") == "Header" and no["c"][0] == 1:
                contagem["nivel_1"] += 1
            elif no.get("t") == "Table":
                contagem["tabelas"] += 1
            elif no.get("t") == "Link" and not no["c"][2][0].startswith("#"):
                urls.add(no["c"][2][0])
            percorrer(no.get("c"))
        elif isinstance(no, list):
            for filho in no:
                percorrer(filho)

    percorrer(json.loads(pypandoc.convert_file(str(markdown), "json", format=FORMATO))["blocks"])
    return contagem["nivel_1"], contagem["tabelas"], urls


def conferir(markdown: Path, docx: Path) -> dict:
    """Reabre o .docx e confere capa, títulos navegáveis, tabelas com grade e links clicáveis."""
    nivel_1_md, tabelas_md, urls_md = _estrutura(markdown)
    documento = Document(str(docx))
    nivel_1 = [p.text for p in documento.paragraphs if p.style.name == "Heading 1"]
    urls = {r.target_ref for r in documento.part.rels.values() if r.reltype == RELATIONSHIP_TYPE.HYPERLINK}
    sem_grade = [i for i, t in enumerate(documento.tables, 1) if "w:tblBorders" not in t.style.element.xml]
    if not any(p.style.name == "Title" for p in documento.paragraphs):
        raise RuntimeError(f"{docx.name}: sem capa; o bloco de metadados (título, data, duração) não foi lido.")
    if len(nivel_1) != nivel_1_md:
        raise RuntimeError(f"{docx.name}: {len(nivel_1)} títulos de nível 1 no Word, {nivel_1_md} no Markdown.")
    if len(documento.tables) != tabelas_md:
        raise RuntimeError(f"{docx.name}: {len(documento.tables)} tabelas no Word, {tabelas_md} no Markdown.")
    if sem_grade:
        raise RuntimeError(f"{docx.name}: tabelas sem grade (estilo sem bordas): {sem_grade}")
    if urls != urls_md:
        raise RuntimeError(f"{docx.name}: links do Word diferentes dos do Markdown: {sorted(urls ^ urls_md)}")
    resumo = {"titulos": sum(p.style.name.startswith("Heading") for p in documento.paragraphs),
              "titulos_nivel_1": nivel_1, "tabelas": len(documento.tables), "links": len(urls),
              "paragrafos": len(documento.paragraphs)}
    log.info("Word conferido: %s (%d títulos, %d tabelas com grade, %d links)", docx.name, resumo["titulos"],
             resumo["tabelas"], resumo["links"])
    return resumo
