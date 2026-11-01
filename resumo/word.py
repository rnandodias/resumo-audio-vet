"""Conversão da apostila de Markdown para Word e conferência do arquivo gerado."""

import logging
from pathlib import Path

import pypandoc
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE

log = logging.getLogger(__name__)


def converter(markdown: Path, destino: Path, titulos_esperados: list[str]) -> dict:
    pypandoc.convert_file(str(markdown), "docx", format="markdown", outputfile=str(destino),
                          extra_args=["--toc", "--toc-depth=3"])
    return conferir(destino, titulos_esperados)


def conferir(docx: Path, titulos_esperados: list[str]) -> dict:
    """Reabre o .docx e confere títulos navegáveis, tabelas reais e links clicáveis."""
    documento = Document(str(docx))
    titulos = [p.text for p in documento.paragraphs if p.style.name.startswith("Heading")]
    nivel_1 = [p.text for p in documento.paragraphs if p.style.name == "Heading 1"]
    links = [r for r in documento.part.rels.values() if r.reltype == RELATIONSHIP_TYPE.HYPERLINK]
    if nivel_1 != titulos_esperados:
        raise RuntimeError(f"Títulos de nível 1 do .docx diferentes do esperado: {nivel_1} != {titulos_esperados}")
    if not any(p.style.name == "Title" for p in documento.paragraphs):
        raise RuntimeError("O .docx não tem capa: o bloco de metadados (título, data, duração) não foi lido.")
    if not documento.tables:
        raise RuntimeError("O .docx não tem nenhuma tabela; a conversão das tabelas Markdown falhou.")
    if not links:
        raise RuntimeError("O .docx não tem nenhum link clicável; a seção de material complementar falhou.")
    resumo = {"titulos": len(titulos), "titulos_nivel_1": nivel_1, "tabelas": len(documento.tables),
              "links": len(links), "paragrafos": len(documento.paragraphs)}
    log.info("Word conferido: %d títulos, %d tabelas, %d links", resumo["titulos"], resumo["tabelas"],
             resumo["links"])
    return resumo
