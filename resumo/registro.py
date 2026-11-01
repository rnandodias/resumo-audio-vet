"""Log da rodada e manifesto da aula, incluindo o consumo real de cada chamada paga."""

import json
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

from resumo.audios import FUSO, Audio

# Preços em dólar (consultados em 01/11/2026). AssemblyAI: por hora de áudio, Universal-3.5 Pro
# (0,21) + keyterms (0,05) + diarização (0,02). Anthropic (claude-opus-5-5): por milhão de tokens.
PRECO_ASSEMBLYAI_HORA = 0.28
PRECO_OPUS = {"entrada": 4.00, "saida": 20.00, "cache_escrita_5m": 5.00, "cache_escrita_1h": 8.00,
              "cache_leitura": 0.20}
PRECO_BUSCA_WEB = 10.00 / 1000


def configurar_log(arquivo: Path) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger()
    raiz.setLevel(logging.DEBUG)
    em_arquivo = logging.FileHandler(arquivo, encoding="utf-8")
    em_arquivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    no_terminal = logging.StreamHandler(sys.stdout)
    no_terminal.setLevel(logging.INFO)
    no_terminal.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    raiz.addHandler(em_arquivo)
    raiz.addHandler(no_terminal)
    for ruidoso in ("httpx", "httpx2", "httpcore", "httpcore2", "anthropic", "assemblyai", "pypandoc"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


def hms(segundos: float) -> str:
    s = round(segundos)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


class Manifesto:
    """manifesto.json da aula. O consumo é acumulado entre rodadas e salvo a cada chamada paga."""

    def __init__(self, caminho: Path, aula: str, slug: str):
        self.caminho = caminho
        self._trava = threading.Lock()
        anterior = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
        self.dados = {"aula": aula, "slug": slug,
                      "consumo": anterior.get("consumo", {"assemblyai": [], "anthropic": []})}

    def registrar_audios(self, audios: list[Audio], duplicatas: list[dict], avisos: list[str]) -> None:
        self.dados.update({
            "atualizado_em": datetime.now(FUSO).isoformat(timespec="seconds"),
            "audios": [{
                "posicao": a.posicao,
                "arquivo": a.arquivo.name,
                "hash_sha256_audio": a.hash,
                "gravado_em": a.gravado_em.isoformat(timespec="seconds"),
                "fonte_da_data": a.fonte_data,
                "duracao_s": round(a.duracao_s, 3),
                "duracao": hms(a.duracao_s),
            } for a in audios],
            "duracao_total": hms(sum(a.duracao_s for a in audios)),
            "duplicatas_ignoradas": duplicatas,
            "avisos": list(avisos),
        })
        self.salvar()

    def registrar_assemblyai(self, referencia: str, segundos: float, transcript_id: str) -> None:
        self.dados["consumo"]["assemblyai"].append({
            "quando": datetime.now(FUSO).isoformat(timespec="seconds"),
            "referencia": referencia,
            "transcript_id": transcript_id,
            "minutos": round(segundos / 60, 2),
            "custo_usd": round(segundos / 3600 * PRECO_ASSEMBLYAI_HORA, 4),
        })
        self.salvar()

    def registrar_anthropic(self, etapa: str, referencia: str, uso: dict) -> None:
        custo = (uso["entrada"] * PRECO_OPUS["entrada"] + uso["saida"] * PRECO_OPUS["saida"]
                 + uso["cache_escrita_5m"] * PRECO_OPUS["cache_escrita_5m"]
                 + uso["cache_escrita_1h"] * PRECO_OPUS["cache_escrita_1h"]
                 + uso["cache_leitura"] * PRECO_OPUS["cache_leitura"]) / 1_000_000
        custo += uso["buscas_web"] * PRECO_BUSCA_WEB
        self.dados["consumo"]["anthropic"].append({
            "quando": datetime.now(FUSO).isoformat(timespec="seconds"),
            "etapa": etapa, "referencia": referencia, **uso, "custo_usd": round(custo, 4)})
        self.salvar()

    def registrar_aviso(self, aviso: str) -> None:
        self.dados["avisos"].append(aviso)
        self.salvar()

    def salvar(self) -> None:
        with self._trava:  # as seções da apostila são geradas em paralelo
            consumo = self.dados["consumo"]
            consumo["total_usd"] = round(sum(c["custo_usd"] for c in consumo["assemblyai"] + consumo["anthropic"]), 4)
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            self.caminho.write_text(json.dumps(self.dados, ensure_ascii=False, indent=2), encoding="utf-8")
