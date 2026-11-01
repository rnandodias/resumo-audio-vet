import os
import subprocess
from pathlib import Path

from resumo.audios import ordenar_e_deduplicar


def _gerar(destino: Path, frequencia: int, criacao: str | None = None) -> Path:
    comando = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={frequencia}:duration=1"]
    if criacao:
        comando += ["-metadata", f"creation_time={criacao}"]
    subprocess.run(comando + [str(destino)], check=True)
    return destino


def test_ordena_pela_data_de_gravacao_e_nao_pelo_nome(tmp_path):
    # Os nomes seguem a ordem inversa da gravação, como acontece na exportação do WhatsApp.
    _gerar(tmp_path / "a.m4a", 300, "2026-10-23T19:00:00Z")
    _gerar(tmp_path / "b.m4a", 400, "2026-10-23T12:00:00Z")
    _gerar(tmp_path / "c.m4a", 500, "2026-10-23T15:00:00Z")
    sem_metadado = _gerar(tmp_path / "d.wav", 600)
    os.utime(sem_metadado, (1_700_000_000, 1_700_000_000))  # 2023-11-14: antes de todos

    audios, duplicatas, avisos = ordenar_e_deduplicar(tmp_path)

    assert [a.arquivo.name for a in audios] == ["d.wav", "b.m4a", "c.m4a", "a.m4a"]
    assert [a.posicao for a in audios] == [1, 2, 3, 4]
    assert audios[0].fonte_data == "mtime"
    assert avisos and "d.wav" in avisos[0]
    assert duplicatas == []


def test_deduplica_pelo_conteudo_do_audio_mesmo_com_bytes_diferentes(tmp_path):
    original = _gerar(tmp_path / "aula.m4a", 440, "2026-10-23T12:00:00Z")
    # Mesmo stream de áudio regravado com metadados diferentes: bytes mudam, áudio não.
    copia = tmp_path / "aula (1).m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(original), "-c", "copy",
                    "-metadata", "title=exportado de novo", str(copia)], check=True)
    _gerar(tmp_path / "outra.m4a", 880, "2026-10-23T13:00:00Z")
    assert original.read_bytes() != copia.read_bytes()

    audios, duplicatas, _ = ordenar_e_deduplicar(tmp_path)

    assert [a.arquivo.name for a in audios] == ["aula.m4a", "outra.m4a"]
    assert duplicatas == [{"arquivo": "aula (1).m4a", "duplicata_de": "aula.m4a", "hash": audios[0].hash}]
