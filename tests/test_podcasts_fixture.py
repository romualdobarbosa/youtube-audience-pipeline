"""A fixture sintética do dbt dos podcasts tem o histórico SCD2 que o CI espera."""

from __future__ import annotations

import sqlite3

from tests.fixtures.make_podcasts_fixture import build


def _query(path, sql):
    with sqlite3.connect(path) as con:
        return con.execute(sql).fetchall()


def test_fixture_tem_historico_e_uma_versao_vigente_por_chave(tmp_path):
    path = tmp_path / "podcasts.db"
    build(path)

    for table, key in [("dim_channel", "channel_id"), ("dim_video", "video_id")]:
        rows = _query(
            path,
            f"select {key}, sum(is_current), sum(valid_to is not null) from {table} group by {key}",
        )
        assert all(current == 1 for _, current, _ in rows)
        assert any(historic > 0 for _, _, historic in rows)
        # Linha histórica tem valid_to; a vigente não.
        inconsistent = f"select count(*) from {table} where is_current = (valid_to is not null)"
        assert _query(path, inconsistent) == [(0,)]

    assert _query(path, "select count(*) from dim_channel")[0][0] == 5
    assert _query(path, "select count(*) from dim_video")[0][0] == 7
    assert _query(path, "select count(*) from fact_channel_metrics")[0][0] == 6
    assert _query(path, "select count(*) from fact_video_metrics")[0][0] == 12


def test_fixture_quebrada_duplica_versao_vigente(tmp_path):
    path = tmp_path / "podcasts.db"
    build(path, broken=True)

    for table, key in [("dim_channel", "channel_id"), ("dim_video", "video_id")]:
        dup = _query(
            path,
            f"select {key} from {table} where is_current = 1 group by {key} having count(*) > 1",
        )
        assert len(dup) == 1
