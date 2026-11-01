"""Etapa 2: transcrição na AssemblyAI (Universal-3.5 Pro, keyterms e diarização), com cache por hash."""

import json
import logging
import os
import time
from pathlib import Path

import assemblyai as aai

from resumo.audios import Audio
from resumo.registro import Manifesto, hms

log = logging.getLogger(__name__)

MODELO = "universal-3-5-pro"
KEYTERMS_MAX_PALAVRAS = 1000
KEYTERMS_MAX_PALAVRAS_POR_TERMO = 6


def ler_glossario(arquivo: Path) -> list[str]:
    linhas = (linha.strip() for linha in arquivo.read_text(encoding="utf-8").splitlines())
    return list(dict.fromkeys(linha for linha in linhas if linha and not linha.startswith("#")))


def keyterms(aula: str, glossario: list[str]) -> list[str]:
    termos = list(dict.fromkeys([aula, *glossario]))
    longos = [t for t in termos if len(t.split()) > KEYTERMS_MAX_PALAVRAS_POR_TERMO]
    total = sum(len(t.split()) for t in termos)
    if longos or total > KEYTERMS_MAX_PALAVRAS:
        raise ValueError(f"Keyterms fora do limite da API ({KEYTERMS_MAX_PALAVRAS} palavras somadas, "
                         f"{KEYTERMS_MAX_PALAVRAS_POR_TERMO} por termo): {total} palavras; termos longos: {longos}")
    return termos


def _alinhar_nomes(pasta: Path, audio: Audio) -> None:
    """O cache é achado pelo hash; se a posição do áudio mudou, os arquivos são renomeados."""
    for arquivo in pasta.glob(f"??-{audio.hash_curto}.*"):
        if not arquivo.name.startswith(audio.nome_base):
            arquivo.rename(pasta / (audio.nome_base + arquivo.name[len(audio.nome_base):]))


def _segmentos(paragrafos: list[dict]) -> list[tuple[int, str, str]]:
    """Parágrafos da AssemblyAI quebrados nas trocas de falante: (início em ms, falante, texto)."""
    segmentos = []
    for paragrafo in paragrafos:
        atual = None
        for palavra in paragrafo["words"]:
            falante = palavra.get("speaker") or "?"
            if atual is None or atual[1] != falante:
                atual = (palavra["start"], falante, [])
                segmentos.append(atual)
            atual[2].append(palavra["text"])
    return [(inicio, falante, " ".join(palavras)) for inicio, falante, palavras in segmentos]


def _escrever_bruta(destino: Path, audio: Audio, transcricao: dict) -> None:
    linhas = [f"# Áudio {audio.posicao} — transcrição bruta", "",
              f"{audio.arquivo.name} · gravado em {audio.gravado_em:%d/%m/%Y %H:%M} · {hms(audio.duracao_s)} · "
              f"modelo {transcricao['transcript'].get('speech_model_used')}", ""]
    for inicio, falante, texto in _segmentos(transcricao["paragraphs"]["paragraphs"]):
        linhas += [f"[{hms(inicio / 1000)}] **Falante {falante}:** {texto}", ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")


class Transcritor:
    def __init__(self, manifesto: Manifesto, termos: list[str]):
        aai.settings.api_key = os.environ["ASSEMBLYAI_API_KEY"]
        aai.settings.http_timeout = 300.0
        self.manifesto = manifesto
        self.cliente = aai.Client.get_default()
        # O SDK 1.8.2 ainda não conhece o Universal-3.5 Pro no enum de resposta e falha ao interpretar o
        # transcript; por isso o SDK monta a config e faz o upload, e envio e leitura usam o cliente HTTP
        # autenticado do próprio SDK, que também entrega o JSON bruto para o cache.
        self.http = self.cliente.http_client
        self.config = aai.TranscriptionConfig(
            speech_models=[MODELO],
            language_code="pt",
            speaker_labels=True,
            speaker_options={"min_speakers_expected": 2, "max_speakers_expected": 8},
            keyterms_prompt=termos,
        )

    def _get(self, caminho: str) -> dict:
        resposta = self.http.get(caminho)
        resposta.raise_for_status()
        return resposta.json()

    def _enviar(self, audio: Audio, arquivo_audio: Path, pendente: Path) -> str:
        log.info("Áudio %d: enviando %s (%s) para a AssemblyAI", audio.posicao, arquivo_audio.name,
                 hms(audio.duracao_s))
        url = aai.Transcriber(client=self.cliente, config=self.config).upload_file(str(arquivo_audio))
        corpo = aai.types.TranscriptRequest(audio_url=url, **self.config.raw.dict(exclude_none=True)).dict(
            exclude_none=True, by_alias=True)
        resposta = self.http.post("/v2/transcript", json=corpo)
        if resposta.status_code != 200:
            raise RuntimeError(f"AssemblyAI recusou o envio do áudio {audio.posicao}: {resposta.text}")
        transcript_id = resposta.json()["id"]
        pendente.write_text(transcript_id, encoding="utf-8")
        return transcript_id

    def transcrever(self, audio: Audio, arquivo_audio: Path, pasta: Path) -> Path:
        """Devolve o caminho da transcrição bruta em Markdown, chamando a API só se não houver cache."""
        pasta.mkdir(parents=True, exist_ok=True)
        _alinhar_nomes(pasta, audio)
        cache = pasta / f"{audio.nome_base}.json"
        bruta = pasta / f"{audio.nome_base}.bruta.md"
        if cache.exists():
            log.info("Áudio %d: transcrição em cache", audio.posicao)
        else:
            # Se uma rodada anterior caiu depois do envio, retoma o mesmo job em vez de pagar de novo.
            pendente = pasta / f"{audio.nome_base}.pendente"
            if pendente.exists():
                transcript_id = pendente.read_text(encoding="utf-8").strip()
                log.info("Áudio %d: retomando o job %s já enviado", audio.posicao, transcript_id)
            else:
                transcript_id = self._enviar(audio, arquivo_audio, pendente)
            while (transcript := self._get(f"/v2/transcript/{transcript_id}"))["status"] not in ("completed", "error"):
                time.sleep(5)
            if transcript["status"] == "error":
                pendente.unlink()
                raise RuntimeError(f"AssemblyAI falhou no áudio {audio.posicao}: {transcript.get('error')}")
            if abs(transcript["audio_duration"] - audio.duracao_s) > 2:
                self.manifesto.registrar_aviso(f"Áudio {audio.posicao}: AssemblyAI recebeu "
                                               f"{hms(transcript['audio_duration'])}, o arquivo tem {hms(audio.duracao_s)}")
            if transcript.get("speech_model_used") != MODELO:
                self.manifesto.registrar_aviso(f"Áudio {audio.posicao}: transcrito com "
                                               f"{transcript.get('speech_model_used')!r}, não {MODELO}")
            paragrafos = self._get(f"/v2/transcript/{transcript_id}/paragraphs")
            cache.write_text(json.dumps({"transcript": transcript, "paragraphs": paragrafos}, ensure_ascii=False,
                                        indent=1), encoding="utf-8")
            pendente.unlink()
            self.manifesto.registrar_assemblyai(audio.nome_base, transcript["audio_duration"], transcript_id)
            log.info("Áudio %d: transcrito (%s)", audio.posicao, hms(transcript["audio_duration"]))
        if not bruta.exists():
            _escrever_bruta(bruta, audio, json.loads(cache.read_text(encoding="utf-8")))
        return bruta
