import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from sqlalchemy import func, distinct, literal
from sqlalchemy.orm import Session, aliased

from db.init import init_db
from db.models import Taoist, DuelRecord


def get_db_overview(session: Session):
    total_taoists = session.query(func.count()).select_from(Taoist).scalar()
    unique_taoist_names = session.query(func.count(distinct(Taoist.name))).scalar()

    # DuelRecord stats
    total_duel_records = session.query(func.count()).select_from(DuelRecord).scalar()
    unique_duel_pairs = session.query(
        func.count(
            distinct(
                DuelRecord.winner_id.op("||")(literal("-")).op("||")(DuelRecord.loser_id)
            )
        )
    ).scalar()

    # Print stats
    print("Taoist Stats:")
    print(f"\tTotal records: {total_taoists}")
    print(f"\tUnique names: {unique_taoist_names}\n")

    print("DuelRecord Stats:")
    print(f"\tTotal records: {total_duel_records}")
    print(f"\tUnique winner-loser pairs: {unique_duel_pairs}")


def get_battle_br_pairs(session):
    # Get total_br for all duels
    WinnerTaoist = aliased(Taoist)
    LoserTaoist = aliased(Taoist)

    records = (
        session.query(DuelRecord, WinnerTaoist, LoserTaoist)
        .join(WinnerTaoist, DuelRecord.winner_id == WinnerTaoist.id)
        .join(LoserTaoist, DuelRecord.loser_id == LoserTaoist.id)
        .all()
    )

    winner_brs = []
    loser_brs = []
    durations = []

    for duel, winner, loser in records:
        if winner.total_br is not None and loser.total_br is not None:
            winner_brs.append(winner.total_br)
            loser_brs.append(loser.total_br)
            durations.append(duel.duration or 0.0)

    return winner_brs, loser_brs, durations


def plot_battle_br(session):
    winner_brs, loser_brs, durations = get_battle_br_pairs(session)

    if not winner_brs:
        print("No valid duel records found.")
        return

    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(winner_brs, loser_brs, c=durations, cmap='viridis', alpha=0.7)
    plt.xlabel("Winner Total BR")
    plt.ylabel("Loser Total BR")
    plt.title("Winner vs Loser BR in Duels (coloured by duration)")
    plt.colorbar(scatter, label="Duration (s)")
    plt.plot([min(winner_brs + loser_brs), max(winner_brs + loser_brs)],
             [min(winner_brs + loser_brs), max(winner_brs + loser_brs)],
             color='gray', linestyle='--', linewidth=1, label="Equal BR line")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()


def plot_taoist_brs_with_labels(session):
    results = session.query(Taoist.name, Taoist.total_br, Taoist.created_at)
    # Create DataFrame
    df = pd.DataFrame(results, columns=["name", "total_br", "date"])
    df["date"] = pd.to_datetime(df["date"])

    # Violin Plot
    plt.figure(figsize=(10, 5))
    sns.violinplot(y=df["total_br"])
    plt.title("Violin Plot of Total BRs")
    plt.ylabel("Total BR")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Time vs BR Plot with Labels
    plt.figure(figsize=(12, 6))
    for name in df["name"].unique():
        sub_df = df[df["name"] == name].sort_values("date")
        plt.plot(sub_df["date"], sub_df["total_br"], marker="o")
        last_row = sub_df.iloc[-1]
        plt.text(last_row["date"], last_row["total_br"], name, fontsize=8, ha='left', va='center')

    plt.title("BR Over Time by Taoist (Labelled)")
    plt.xlabel("Date")
    plt.ylabel("Total BR")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    db = init_db()
    get_db_overview(db)
    plot_battle_br(db)
    plot_taoist_brs_with_labels(db)
    db.close()
