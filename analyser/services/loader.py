import os
import json
import zipfile
import pandas as pd


class FileLoadError(Exception):
    """Custom exception for file loading errors, such as unsupported file types or corrupted files."""
    pass


def _load_csv(path):
    try:
        return pd.read_csv(path, encoding="utf-8", sep=None, engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", sep=None, engine="python")


def _load_excel(path):
    return pd.read_excel(path)


def _unwrap_json(obj):
    # already list: seedha records hain
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # dict ke andar pehli aisi value dhoondo jo list of dicts ho
        for value in obj.values():
            if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
                return value
        # nahi mili: poora dict ek hi row maan lo
        return [obj]
    raise FileLoadError("The file is corrupted or has an invalid format.")


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = _unwrap_json(data)
    return pd.json_normalize(records)


def _stringify_nested(df):
    # list/dict wale cells ko JSON string bana do, taaki duplicated(), nunique() na tute
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(
                lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v
            )
    return df


def load_file(path):
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".csv":
            df = _load_csv(path)
        elif ext == ".xlsx":
            df = _load_excel(path)
        elif ext == ".json":
            df = _load_json(path)
        else:
            raise FileLoadError("Ye file type supported nahi hai.")
    except FileLoadError:
        raise
    except pd.errors.EmptyDataError:
        raise FileLoadError("The file is empty.")
    except (pd.errors.ParserError, ValueError, zipfile.BadZipFile):
        raise FileLoadError("The file is corrupted or has an invalid format.")

    if df.empty:
        raise FileLoadError("No data was found in the file.")

    df = _stringify_nested(df)
    return df