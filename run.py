"""Pipeline de uma aula: áudios em input/ -> transcrição -> limpeza -> apostila em Markdown e Word.

Uso: python run.py --aula "Anatomia Dermatológica"
"""

import argparse
import logging
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from resumo.apostila import TITULOS_NIVEL_1, Apostila
from resumo.audios import extrair, ordenar_e_deduplicar
from resumo.claude import Claude
from resumo.limpeza import limpar
from resumo.registro import Manifesto, configurar_log, hms
from resumo.transcricao import Transcritor, keyterms, ler_glossario
from resumo.word import converter

RAIZ = Path(__file__).parent
GLOSSARIO = RAIZ / "glossario" / "dermato-vet.txt"

log = logging.getLogger("run")


def slugificar(nome: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--aula", required=True, help="nome da aula, usado na apostila e no slug da pasta")
    aula = parser.parse_args().aula

    load_dotenv(RAIZ / ".env")
    faltando = [chave for chave in ("ASSEMBLYAI_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(chave)]
    if faltando:
        raise SystemExit(f"Faltam chaves no .env: {', '.join(faltando)}")

    slug = slugificar(aula)
    pasta = RAIZ / "output" / slug
    configurar_log(pasta / "log.txt")
    manifesto = Manifesto(pasta / "manifesto.json", aula, slug)
    log.info("Aula '%s' -> output/%s", aula, slug)

    log.info("Etapa 1: ordenar e deduplicar os áudios")
    audios, duplicatas, avisos = ordenar_e_deduplicar(RAIZ / "input")
    manifesto.registrar_audios(audios, duplicatas, avisos)
    for audio in audios:
        log.info("  %d. %s  gravado %s  %s", audio.posicao, audio.arquivo.name, f"{audio.gravado_em:%d/%m %H:%M}",
                 hms(audio.duracao_s))
    log.info("  %d áudios únicos, %s no total; %d duplicata(s) ignorada(s)", len(audios),
             hms(sum(a.duracao_s for a in audios)), len(duplicatas))
    extraidos = [extrair(audio, pasta / "audio") for audio in audios]

    log.info("Etapa 2: transcrição na AssemblyAI")
    glossario = ler_glossario(GLOSSARIO)
    transcritor = Transcritor(manifesto, keyterms(aula, glossario))
    with ThreadPoolExecutor(max_workers=len(audios)) as executor:
        brutas = list(executor.map(transcritor.transcrever, audios, extraidos,
                                   [pasta / "transcricoes"] * len(audios)))

    log.info("Etapa 3: limpeza das transcrições com Opus 5.5")
    claude = Claude(manifesto)
    with ThreadPoolExecutor(max_workers=4) as executor:
        limpas = list(executor.map(lambda a, b: limpar(claude, a, b, aula, glossario), audios, brutas))

    log.info("Etapa 4: apostila com Opus 5.5 e busca web")
    markdown = pasta / "apostila.md"
    markdown.write_text(Apostila(claude, manifesto, pasta, aula, glossario, audios, limpas).gerar(), encoding="utf-8")
    conferencia = converter(markdown, pasta / "apostila.docx", TITULOS_NIVEL_1)
    manifesto.dados["word"] = conferencia
    manifesto.salvar()

    log.info("Pronto: %s e %s", markdown.relative_to(RAIZ), (pasta / "apostila.docx").relative_to(RAIZ))
    log.info("Custo acumulado desta aula: US$ %.2f", manifesto.dados["consumo"]["total_usd"])


if __name__ == "__main__":
    main()
