import random

import joblib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.linear_model import LogisticRegression

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler

from db.init import init_db
from db.models import DuelRecord, Taoist


def extract_duel_data(session, rel_br: float = 0.1):
    """ Grab all the data from the database. Return a set with 50% win and 50% lose.

    Parameters
    ----------
    session
        The database session to retrieve records from.
    rel_br : float
        The maximum relative BR difference for a duel to be considered for the data.

    Returns
    -------
    df : pd.Dataframe
        The records of all applicable duels + label column for win/lose.
    """
    duels = session.query(DuelRecord).all()
    records = []

    for duel in duels:
        a, b = (duel.winner, duel.loser)
        label = 1

        # Add toggle for keeping duels within a relative BR
        if a.total_br < b.total_br:
            rel_diff = (b.total_br - a.total_br) / a.total_br
        else:
            rel_diff = (a.total_br - b.total_br) / b.total_br
        if rel_diff > rel_br:
            continue

        if random.random() < 0.5:
            # Flip A and B 50% of the time since otherwise the winner would always be A.
            a, b = b, a
            label = 0

        record = {"label": label}
        # Flatten Taoist attributes with A_/B_ prefix
        for col in a.__table__.columns.keys():
            if col == "id":
                continue
            record[f"A_{col}"] = getattr(a, col)
        for col in b.__table__.columns.keys():
            if col == "id":
                continue
            record[f"B_{col}"] = getattr(b, col)

        records.append(record)

    df = pd.DataFrame(records)
    print(f"Using {len(df)}/{len(duels)} duels with BR difference < {rel_br * 100:2.1f}%")
    return df


def train_total_br_model(df, save_path="total_br_model.joblib"):
    y = df["label"].values
    X = df[['A_total_br', 'B_total_br']].copy()
    X["br_diff"] = X["A_total_br"] - X["B_total_br"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.25, random_state=42)

    pipe = make_pipeline(
        SimpleImputer(strategy="mean"),
        MinMaxScaler(),
        LogisticRegression()
    )

    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(f"AUC: {roc_auc_score(y_test, y_proba):.3f}")

    plt.scatter((X_test["A_total_br"]/X_test["B_total_br"])*100 - 100, y_proba)
    plt.xlabel("Relative BR")
    plt.ylabel("Probability of winning")
    plt.show()

    # Save to disk
    joblib.dump(pipe, save_path)
    print(f"Model saved to: {save_path}")


if __name__ == "__main__":
    db = init_db()
    train_total_br_model(extract_duel_data(db, 1e8))
