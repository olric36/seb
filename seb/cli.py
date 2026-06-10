"""Komut satırı arayüzü."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from seb.database import DatabaseManager
from seb.predictor import HorseRacingPredictor


@click.group()
@click.version_option(package_name="seb")
@click.option("--db", default="seb_yarislar.db", help="Veritabanı dosya yolu")
@click.option("-v", "--verbose", is_flag=True, help="Detaylı çıktı")
@click.pass_context
def main(ctx: click.Context, db: str, verbose: bool) -> None:
    """SEB — At Yarışı Tahmin Aracı"""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# ── TJK Veri Çekme ──────────────────────────────────────────────────────────


@main.command()
@click.option("--months", default=6, help="Kaç ay geriye gidilecek (varsayılan 6)")
@click.option("--csv", "csv_path", default=None, help="CSV olarak da kaydet (opsiyonel)")
@click.pass_context
def fetch(ctx: click.Context, months: int, csv_path: str | None) -> None:
    """TJK'dan son N aylık Türkiye yarış verilerini çek ve veritabanına kaydet."""
    from seb.tjk_scraper import scrape_tjk

    db_path = ctx.obj["db_path"]
    click.echo(f"TJK'dan son {months} aylık veriler çekiliyor...")

    df = scrape_tjk(months=months, output_path=csv_path)

    if df.empty:
        click.echo("Veri bulunamadı.", err=True)
        sys.exit(1)

    click.echo(f"{len(df)} kayıt çekildi. Veritabanına aktarılıyor...")

    db = DatabaseManager(db_path)
    db.create_tables()
    counts = db.import_from_dataframe(df)

    click.echo("Veritabanı güncellendi:")
    for tablo, sayi in counts.items():
        click.echo(f"  {tablo}: {sayi}")


@main.command()
@click.argument("tarih")
@click.option("--csv", "csv_path", default=None, help="CSV olarak da kaydet (opsiyonel)")
@click.pass_context
def fetch_date(ctx: click.Context, tarih: str, csv_path: str | None) -> None:
    """Belirli bir tarih için TJK yarış sonuçlarını çek (format: YYYY-MM-DD)."""
    from datetime import datetime

    from seb.tjk_scraper import scrape_tjk_single_date

    db_path = ctx.obj["db_path"]

    try:
        race_date = datetime.strptime(tarih, "%Y-%m-%d").date()
    except ValueError:
        click.echo("Hata: Tarih formatı YYYY-MM-DD olmalı (ör: 2026-06-01)", err=True)
        sys.exit(1)

    click.echo(f"{tarih} tarihli yarışlar çekiliyor...")

    df = scrape_tjk_single_date(race_date)

    if df.empty:
        click.echo(f"{tarih} tarihinde Türkiye'de yarış bulunamadı.")
        return

    if csv_path:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        click.echo(f"CSV kaydedildi: {csv_path}")

    click.echo(f"{len(df)} kayıt çekildi. Veritabanına aktarılıyor...")

    db = DatabaseManager(db_path)
    db.create_tables()
    counts = db.import_from_dataframe(df)

    click.echo("Veritabanı güncellendi:")
    for tablo, sayi in counts.items():
        click.echo(f"  {tablo}: {sayi}")


# ── Veritabanı İstatistikleri ────────────────────────────────────────────────


@main.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Veritabanı istatistiklerini göster."""
    db_path = ctx.obj["db_path"]
    db = DatabaseManager(db_path)

    if not Path(db_path).exists():
        click.echo("Veritabanı bulunamadı. Önce 'seb fetch' ile veri çekin.", err=True)
        sys.exit(1)

    istatistikler = db.get_statistics()
    click.echo("Veritabanı İstatistikleri:")
    for tablo, sayi in istatistikler.items():
        click.echo(f"  {tablo}: {sayi}")


@main.command()
@click.option("--min-yaris", default=3, help="Minimum yarış sayısı filtresi")
@click.option("--limit", "row_limit", default=20, help="Gösterilecek at sayısı")
@click.pass_context
def at_stats(ctx: click.Context, min_yaris: int, row_limit: int) -> None:
    """At bazlı istatistikleri göster."""
    db_path = ctx.obj["db_path"]
    db = DatabaseManager(db_path)

    results = db.query_at_istatistikleri(min_yaris=min_yaris)
    if not results:
        click.echo("Yeterli veri bulunamadı.")
        return

    header = f"{'At':<25} {'Irk':<10} {'Yarış':<7} {'1.':<5} {'İlk 3':<7} {'Oran':<7} {'Ganyan':<8}"
    click.echo(f"\n{header}")
    click.echo("-" * 72)
    for r in results[:row_limit]:
        click.echo(
            f"{r['at']:<25} {(r['irk'] or '-'):<10} {r['toplam_yaris']:<7} "
            f"{r['birincilik']:<5} {r['ilk_uc']:<7} "
            f"{r['kazanma_orani']:<7.3f} {r['ort_ganyan'] or '-':<8}"
        )


@main.command()
@click.option("--min-yaris", default=5, help="Minimum yarış sayısı filtresi")
@click.option("--limit", "row_limit", default=20, help="Gösterilecek jokey sayısı")
@click.pass_context
def jokey_stats(ctx: click.Context, min_yaris: int, row_limit: int) -> None:
    """Jokey bazlı istatistikleri göster."""
    db_path = ctx.obj["db_path"]
    db = DatabaseManager(db_path)

    results = db.query_jokey_istatistikleri(min_yaris=min_yaris)
    if not results:
        click.echo("Yeterli veri bulunamadı.")
        return

    click.echo(f"\n{'Jokey':<25} {'Yarış':<7} {'1.':<5} {'İlk 3':<7} {'Oran':<7}")
    click.echo("-" * 55)
    for r in results[:row_limit]:
        click.echo(
            f"{r['jokey']:<25} {r['toplam_yaris']:<7} "
            f"{r['birincilik']:<5} {r['ilk_uc']:<7} "
            f"{r['kazanma_orani']:<7.3f}"
        )


@main.command()
@click.pass_context
def mesafe_stats(ctx: click.Context) -> None:
    """Mesafe bazlı yarış istatistiklerini göster."""
    db_path = ctx.obj["db_path"]
    db = DatabaseManager(db_path)

    results = db.query_mesafe_istatistikleri()
    if not results:
        click.echo("Yeterli veri bulunamadı.")
        return

    click.echo(f"\n{'Mesafe (m)':<12} {'Kategori':<12} {'Yarış Sayısı':<12}")
    click.echo("-" * 36)
    for r in results:
        click.echo(f"{r['metre']:<12} {r['kategori']:<12} {r['toplam_yaris']:<12}")


# ── Tahmin Modeli ────────────────────────────────────────────────────────────


@main.command()
@click.option("--data", required=True, type=click.Path(exists=True), help="Yarış verisi CSV")
@click.option("--output", default="model.joblib", help="Model kayıt yolu")
@click.option("--estimators", default=100, help="Random Forest ağaç sayısı")
@click.option("--max-depth", default=10, help="Maksimum ağaç derinliği")
def train(data: str, output: str, estimators: int, max_depth: int) -> None:
    """Tahmin modelini eğit."""
    from seb.data_loader import load_race_data
    from seb.features import build_feature_matrix

    click.echo(f"Veri yükleniyor: {data}")

    try:
        races = load_race_data(data)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Hata: {e}", err=True)
        sys.exit(1)

    click.echo(f"{len(races)} yarış yüklendi")

    X, y = build_feature_matrix(races)
    if X.empty:
        click.echo("Hata: Özellik matrisi boş — yeterli veri yok", err=True)
        sys.exit(1)

    click.echo(f"Özellik matrisi: {X.shape[0]} örnek, {X.shape[1]} özellik")

    predictor = HorseRacingPredictor(
        n_estimators=estimators,
        max_depth=max_depth,
    )
    predictor.fit(X, y)

    predictor.save(output)
    click.echo(f"Model kaydedildi: {output}")

    importances = predictor.feature_importances()
    click.echo("\nEn önemli 5 özellik:")
    for i, (name, score) in enumerate(list(importances.items())[:5], 1):
        click.echo(f"  {i}. {name}: {score:.4f}")
