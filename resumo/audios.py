"""Etapa 1: localizar os áudios, ordenar pela data de gravação, deduplicar e extrair."""

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

EXTENSOES = {".mp4", ".m4a", ".mp3", ".ogg", ".opus", ".wav"}
FUSO = ZoneInfo("America/Sao_Paulo")

log = logging.getLogger(__name__)


@dataclass
class Audio:
    arquivo: Path
    hash: str
    gravado_em: datetime
    fonte_data: str
    duracao_s: float
    posicao: int = 0

    @property
    def hash_curto(self) -> str:
        return self.hash[:12]

    @property
    def nome_base(self) -> str:
        return f"{self.posicao:02d}-{self.hash_curto}"


def _executar(comando: list[str]) -> str:
    return subprocess.run(comando, capture_output=True, text=True, check=True, encoding="utf-8").stdout


def hash_audio(arquivo: Path) -> str:
    """SHA-256 dos pacotes do stream de áudio, sem o contêiner.

    O hash do arquivo inteiro não serve: o WhatsApp exporta o mesmo áudio com carimbos de
    tempo diferentes no átomo de metadados do MP4, o que muda bytes sem mudar o conteúdo.
    """
    saida = _executar(["ffmpeg", "-v", "error", "-i", str(arquivo), "-map", "0:a:0", "-c", "copy",
                       "-f", "hash", "-hash", "sha256", "-"])
    return saida.strip().split("=", 1)[1]


def ler_audio(arquivo: Path) -> Audio:
    sonda = json.loads(_executar(["ffprobe", "-v", "error", "-print_format", "json",
                                  "-show_format", "-show_streams", str(arquivo)]))
    tags = [sonda["format"].get("tags", {})] + [s.get("tags", {}) for s in sonda["streams"]]
    criacao = next((t["creation_time"] for t in tags if "creation_time" in t), None)
    if criacao:
        gravado_em = datetime.fromisoformat(criacao.replace("Z", "+00:00"))
        fonte = "creation_time"
    else:
        gravado_em = datetime.fromtimestamp(arquivo.stat().st_mtime, tz=timezone.utc)
        fonte = "mtime"
    return Audio(arquivo=arquivo, hash=hash_audio(arquivo), gravado_em=gravado_em.astimezone(FUSO),
                 fonte_data=fonte, duracao_s=float(sonda["format"]["duration"]))


def ordenar_e_deduplicar(pasta: Path) -> tuple[list[Audio], list[dict], list[str]]:
    """Retorna (áudios únicos em ordem de gravação, duplicatas ignoradas, avisos)."""
    arquivos = sorted(p for p in pasta.iterdir() if p.suffix.lower() in EXTENSOES)
    # Entre cópias do mesmo áudio fica a de nome mais curto (sem o sufixo " (1)" do WhatsApp).
    audios = sorted((ler_audio(p) for p in arquivos), key=lambda a: (len(a.arquivo.name), a.arquivo.name))
    unicos: dict[str, Audio] = {}
    duplicatas, avisos = [], []
    for audio in audios:
        if audio.hash in unicos:
            original = unicos[audio.hash].arquivo.name
            duplicatas.append({"arquivo": audio.arquivo.name, "duplicata_de": original, "hash": audio.hash})
            log.info("Duplicata ignorada: %s (mesmo áudio que %s)", audio.arquivo.name, original)
            continue
        unicos[audio.hash] = audio
        if audio.fonte_data == "mtime":
            aviso = f"{audio.arquivo.name}: sem metadado creation_time; ordenado pela data de modificação"
            avisos.append(aviso)
            log.warning(aviso)
    ordenados = sorted(unicos.values(), key=lambda a: (a.gravado_em, a.arquivo.name))
    for posicao, audio in enumerate(ordenados, start=1):
        audio.posicao = posicao
    return ordenados, duplicatas, avisos


def extrair(audio: Audio, pasta: Path) -> Path:
    """Converte para FLAC mono 16 kHz (sem perda adicional sobre o AAC de origem)."""
    destino = pasta / f"{audio.nome_base}.flac"
    if not destino.exists():
        pasta.mkdir(parents=True, exist_ok=True)
        # Grava num arquivo provisório: uma extração interrompida nunca vira cache e nunca é enviada paga.
        provisorio = destino.with_name(f"{audio.nome_base}.parcial.flac")
        _executar(["ffmpeg", "-v", "error", "-y", "-i", str(audio.arquivo), "-vn", "-ac", "1", "-ar", "16000",
                   "-c:a", "flac", str(provisorio)])
        provisorio.replace(destino)
        log.info("Áudio extraído: %s", destino.name)
    return destino
