
import pandas as pd


def clean_columns(df):
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def remove_duplicates(df):
    df = df.copy()
    df = df.drop_duplicates()

    return df


def clean_data(df):
    df = clean_columns(df)
    df = remove_duplicates(df)

    return df
