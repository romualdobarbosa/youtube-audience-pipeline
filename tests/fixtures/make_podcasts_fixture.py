"""Gera um SQLite pequeno e determinístico pro dbt dos podcasts (dbt/) rodar no CI.

Usa o schema real (src/database.py::Base) e dados sintéticos: 2 canais e 4 vídeos,
com histórico SCD2 (versões antigas com valid_to preenchido e is_current = 0, uma
versão vigente por chave) e 3 coletas de métricas apontando pra versão vigente na
época de cada coleta. Nada aqui toca data/youtube.db nem o Turso.

    uv run --group dbt-podcasts python -m tests.fixtures.make_podcasts_fixture CAMINHO.db
    ... --broken   # duplica a versão vigente de um canal e de um vídeo (invariante quebrada)
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database import Base, DimChannel, DimVideo, FactChannelMetrics, FactVideoMetrics

# Três coletas; as mudanças de atributo acontecem entre elas.
COLLECTIONS = [datetime(2026, 9, 1, 12), datetime(2026, 9, 8, 12), datetime(2026, 9, 15, 12)]
T0, T1, T2 = COLLECTIONS

# (channel_id, [(valid_from, valid_to, name, handle)]) — a última versão é a vigente.
CHANNELS = [
    (
        "UCfixture000000000000001",
        [
            (T0, T1, "Podcast Fixture", "@podcastfixture"),
            (T1, T2, "Podcast Fixture Oficial", "@podcastfixture"),
            (T2, None, "Podcast Fixture Oficial", "@podcastfixtureoficial"),
        ],
    ),
    (
        "UCfixture000000000000002",
        [
            (T0, T2, "Outro Cast", "@outrocast"),
            (T2, None, "Outro Cast BR", "@outrocast"),
        ],
    ),
]

# (video_id, channel_id, duration_seconds, published_at, [(valid_from, valid_to, title)])
VIDEOS = [
    (
        "vidfixture01",
        "UCfixture000000000000001",
        5400,
        "2026-08-03T20:00:00Z",
        [(T0, T1, "Episódio 1"), (T1, None, "Episódio 1 - com convidado")],
    ),
    (
        "vidfixture02",
        "UCfixture000000000000001",
        45,
        "2026-08-05T15:00:00Z",
        [(T0, None, "Corte do episódio 1")],
    ),
    (
        "vidfixture03",
        "UCfixture000000000000002",
        3600,
        "2026-08-10T21:00:00Z",
        [(T0, T1, "Ep 10"), (T1, T2, "Ep 10 (reupload)"), (T2, None, "Ep 10 - completo")],
    ),
    (
        "vidfixture04",
        "UCfixture000000000000002",
        60,
        "2026-08-12T18:00:00Z",
        [(T0, None, "Melhores momentos")],
    ),
]


def _version_at(versions: list, collected_at: datetime):
    """Versão (linha da dimensão) vigente no instante da coleta."""
    for row in versions:
        if row.valid_from <= collected_at and (row.valid_to is None or collected_at < row.valid_to):
            return row
    raise ValueError(f"nenhuma versão vigente em {collected_at}")


def build(path: Path, broken: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for i, (channel_id, versions) in enumerate(CHANNELS):
            rows = [
                DimChannel(
                    channel_id=channel_id,
                    name=name,
                    handle=handle,
                    country="BR",
                    channel_created_at="2020-01-01T00:00:00Z",
                    valid_from=valid_from,
                    valid_to=valid_to,
                    is_current=valid_to is None,
                )
                for valid_from, valid_to, name, handle in versions
            ]
            session.add_all(rows)
            session.flush()
            for n, collected_at in enumerate(COLLECTIONS):
                session.add(
                    FactChannelMetrics(
                        channel_id=channel_id,
                        channel_key=_version_at(rows, collected_at).channel_key,
                        collected_at=collected_at,
                        subscriber_count=100_000 * (i + 1) + 1_000 * n,
                        total_views=10_000_000 * (i + 1) + 50_000 * n,
                        video_count=2 + n,
                    )
                )

        for i, (video_id, channel_id, duration, published_at, versions) in enumerate(VIDEOS):
            rows = [
                DimVideo(
                    video_id=video_id,
                    channel_id=channel_id,
                    title=title,
                    video_type="short" if duration <= 180 else "long",
                    duration_seconds=duration,
                    category_id="22",
                    default_language="pt",
                    definition="hd",
                    has_caption=False,
                    tags='["podcast"]',
                    published_at=published_at,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    is_current=valid_to is None,
                )
                for valid_from, valid_to, title in versions
            ]
            session.add_all(rows)
            session.flush()
            for n, collected_at in enumerate(COLLECTIONS):
                views = 10_000 * (i + 1) * (n + 1)
                session.add(
                    FactVideoMetrics(
                        video_id=video_id,
                        video_key=_version_at(rows, collected_at).video_key,
                        collected_at=collected_at,
                        views=views,
                        likes=views // 20,
                        comments=views // 100,
                        favorites=0,
                    )
                )

        if broken:
            # Segunda linha is_current = 1 pra mesma chave: o que os testes
            # assert_single_current_channel/video existem pra pegar.
            session.add(
                DimChannel(
                    channel_id=CHANNELS[0][0],
                    name="Duplicada",
                    valid_from=T2,
                    is_current=True,
                )
            )
            session.add(
                DimVideo(
                    video_id=VIDEOS[0][0],
                    channel_id=VIDEOS[0][1],
                    title="Duplicada",
                    video_type="long",
                    valid_from=T2,
                    is_current=True,
                )
            )

        session.commit()
    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="arquivo SQLite de saída (sobrescrito)")
    parser.add_argument("--broken", action="store_true", help="quebra a invariante SCD2")
    args = parser.parse_args()
    build(args.path, broken=args.broken)


if __name__ == "__main__":
    main()
