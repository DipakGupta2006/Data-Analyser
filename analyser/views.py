from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Dataset
from .forms import DatasetForm
from django.contrib import messages
from .services.loader import load_file, FileLoadError
import pandas as pd
from django.core.paginator import Paginator


@login_required(login_url="login")
def home_view(request):
    if request.method == "POST":
        form = DatasetForm(request.POST, request.FILES)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.user = request.user
            dataset.save()
            messages.success(request, "File uploaded successfully.")
            return redirect("home")
    else:
        form = DatasetForm()

    datasets = Dataset.objects.filter(user = request.user).order_by("-uploaded_at")
    return render(request, "analyser/home.html", {"form": form, "datasets": datasets})


@login_required(login_url="login")
def delete_dataset(request, pk):
    dataset = Dataset.objects.get(pk=pk, user=request.user)
    if dataset:
        dataset.file.delete()  # Delete the file from storage
        dataset.delete()
        messages.success(request, "Dataset deleted successfully.")
    else:
        messages.error(request, "Dataset not found or you don't have permission to delete it.")
    return redirect("home")



@login_required(login_url="login")
def analyze_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, user=request.user)

    try:
        df = load_file(dataset.file.path)
    except FileLoadError as e:
        messages.error(request, str(e))
        return redirect("home")

    warnings = []

    # --- Duplicate column names (sabse pehle clean karo) ---
    if df.columns.duplicated().any():
        dups = df.columns[df.columns.duplicated()].unique().tolist()
        warnings.append(f"Duplicate column names: {dups} (sirf pehla rakha gaya)")
        df = df.loc[:, ~df.columns.duplicated()]

    # --- Overview ---
    shape = df.shape
    rows, cols = df.shape
    memory_mb = round(df.memory_usage(deep=True).sum() / 1024**2, 2)
    duplicate_rows = int(df.duplicated().sum())
    total_cells = int(df.size)
    total_missing = int(df.isnull().sum().sum())

    # --- Preview ---
    head = df.head().to_html(classes="table", index=False)
    tail = df.tail().to_html(classes="table", index=False)

    # --- Columns ---
    columns = list(df.columns)
    dtypes = df.dtypes.astype(str).to_dict()
    unique_counts = df.nunique().to_dict()

    # --- Missing ---
    missing_count = df.isnull().sum().to_dict()
    missing_pct = (df.isnull().mean() * 100).round(2).to_dict()

    # --- Numeric ---
    num_df = df.select_dtypes(include="number")
    if num_df.empty:
        describe, skew, corr = "", {}, ""
    else:
        describe = num_df.describe().round(2).to_html(classes="table")
        skew = num_df.skew().round(2).to_dict()
        corr = num_df.corr().round(2).to_html(classes="table")

    # --- Categorical ---
    cat_df = df.select_dtypes(include=["object", "category"])
    top_values = {
        col: cat_df[col].value_counts().head(5).to_dict()
        for col in cat_df.columns
    }

    # --- Outliers (IQR) ---
    outliers = {}
    for col in num_df.columns:
        s = num_df[col].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = int(((s < low) | (s > high)).sum())
        outliers[col] = {
            "count": count,
            "pct": round(count / len(s) * 100, 2),
            "low": round(float(low), 2),
            "high": round(float(high), 2),
        }

    # --- Duplicate rows preview ---
    dup_preview = df[df.duplicated(keep=False)].head(10).to_html(classes="table", index=False)

    # --- Datetime ---
    datetime_cols = {}

    # text me stored dates (CSV)
    for col in cat_df.columns:
        s = cat_df[col].dropna().astype(str)
        if s.empty:
            continue
        parsed = pd.to_datetime(s, errors="coerce", format="mixed")
        if parsed.notna().mean() > 0.9:
            datetime_cols[col] = {
                "min": str(parsed.min().date()),
                "max": str(parsed.max().date()),
                "range_days": int((parsed.max() - parsed.min()).days),
            }

    # real datetime dtype (xlsx)
    dt_df = df.select_dtypes(include="datetime")
    for col in dt_df.columns:
        s = dt_df[col].dropna()
        if not s.empty:
            datetime_cols[col] = {
                "min": str(s.min().date()),
                "max": str(s.max().date()),
                "range_days": int((s.max() - s.min()).days),
            }

    # --- Warnings ---
    for col, pct in missing_pct.items():
        if pct == 100:
            warnings.append(f"'{col}' is completely empty (100% missing)")
        elif pct > 50:
            warnings.append(f"'{col}' has {pct}% missing values")

    for col in df.columns:
        if missing_pct[col] < 100 and df[col].nunique(dropna=True) <= 1:
            warnings.append(f"'{col}' is constant (only one distinct value)")

    for col in cat_df.columns:
        if col not in datetime_cols and len(df) > 0 and df[col].nunique() / len(df) > 0.9:
            warnings.append(f"'{col}' has high cardinality (almost all values are unique)")

    for col in cat_df.columns:
        s = cat_df[col].dropna()
        if not s.empty and pd.to_numeric(s, errors="coerce").notna().mean() > 0.9:
            warnings.append(f"'{col}' appears numeric but is stored as text")

    for col in cat_df.columns:
        if cat_df[col].dropna().map(type).nunique() > 1:
            warnings.append(f"'{col}' contains mixed types")

    if duplicate_rows > 0:
        warnings.append(f"{duplicate_rows} duplicate rows found")

    context = {
        "dataset": dataset,
        "shape": shape, "rows": rows, "cols": cols,
        "memory_mb": memory_mb,
        "duplicate_rows": duplicate_rows,
        "total_cells": total_cells, "total_missing": total_missing,
        "head": head, "tail": tail,
        "columns": columns, "dtypes": dtypes, "unique_counts": unique_counts,
        "missing_count": missing_count, "missing_pct": missing_pct,
        "describe": describe, "skew": skew,
        "top_values": top_values, "corr": corr,
        "outliers": outliers, "dup_preview": dup_preview,
        "datetime_cols": datetime_cols,
        "warnings": warnings,
    }
    return render(request, "analyser/report.html", context)



@login_required(login_url="login")
def preview_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, user=request.user)

    try:
        df = load_file(dataset.file.path)
    except FileLoadError as e:
        messages.error(request, str(e))
        return redirect("home")

    paginator = Paginator(range(len(df)), 50)          # 100 rows per page
    page_obj = paginator.get_page(request.GET.get("page"))

    start = page_obj.start_index() - 1                   # 0-based
    end = page_obj.end_index()
    table = df.iloc[start:end].to_html(classes="table", index=True)

    context = {
        "dataset": dataset,
        "rows": df.shape[0],
        "cols": df.shape[1],
        "table": table,
        "page_obj": page_obj,
    }
    return render(request, "analyser/preview.html", context)