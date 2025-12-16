"""Fixed ASC file processing and conversion to maintain consistent column structure."""

import logging
import re
from pathlib import Path
from typing import Optional

import chardet
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def load_and_process_asc_file(file_name):
    """Load ASC file and return DataFrame with consistent column structure.

    This function carefully preserves the original column structure to avoid
    dimension mismatches when loading into trained models.
    """
    content = ""
    try:
        # Detect file encoding
        with open(file_name, "rb") as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        file_encoding = result["encoding"]

        # Try to read the file with the detected encoding
        try:
            with open(file_name, "r", encoding=file_encoding) as file:
                content = file.read()
        except UnicodeDecodeError:
            # If that fails, try with 'latin-1' encoding
            with open(file_name, "r", encoding="latin-1") as file:
                content = file.read()

        lines = content.split("\n")

        # Find the start of the data
        data_start = 0
        for i, line in enumerate(lines):
            # Check if the line contains tab-separated values and starts with a number-like string
            if "\t" in line and re.match(r"^[\d,.]+\t", line.strip()):
                data_start = i
                break

        if data_start == 0:
            raise ValueError("Could not find the start of data in the file.")

        # Extract header and data
        header = lines[data_start - 1].split("\t")
        data = [line.split("\t") for line in lines[data_start:] if line.strip()]

        # Ensure all data rows have the same number of columns as the header
        max_columns = len(header)
        data = [row for row in data if len(row) == max_columns]

        # CRITICAL: Rename duplicate columns systematically
        # This ensures the same file always produces the same column names
        new_header = []
        seen = {}
        for i, item in enumerate(header):
            item = item.strip()  # Remove leading/trailing whitespace
            if item in seen:
                seen[item] += 1
                new_header.append(f"{item}_{seen[item]}")
            else:
                seen[item] = 0
                new_header.append(item)

        df = pd.DataFrame(data, columns=new_header)

        # Convert columns to appropriate types
        for col in df.columns:
            df[col] = df[col].apply(lambda x: x.replace(",", ".") if isinstance(x, str) else x)
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # CRITICAL: Remove empty columns (all NaN or empty header names) BEFORE filling
        # This matches the behavior in model training which uses .dropna(axis=1, how="all")
        # Empty columns without data cause dimension mismatches between files
        columns_to_keep = []
        for col in df.columns:
            # Keep column if it has a non-empty name and has at least some non-NaN data
            has_name = col.strip() != ""
            has_data = not df[col].isna().all()
            if has_name and has_data:
                columns_to_keep.append(col)

        if len(columns_to_keep) < len(df.columns):
            removed_count = len(df.columns) - len(columns_to_keep)
            logger.info(f"Removed {removed_count} empty column(s) from the data")

        df = df[columns_to_keep]

        # CRITICAL: Fill remaining NaN values with 0 to maintain consistent structure
        df = df.fillna(0.0)

        logging.info(f"Successfully loaded ASC file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        logging.error(f"Error loading ASC file: {str(e)}")
        if content:
            lines_list = content.split("\n")[:10]
            logging.error(f"File content (first 10 lines): {lines_list}")
        else:
            logging.error("Unable to read file content")
        raise


def load_and_process_csv_file(file_name):
    """Load CSV file with consistent handling."""
    df = pd.read_csv(file_name)

    # Remove empty columns (all NaN or empty names) to match training behavior
    columns_to_keep = []
    for col in df.columns:
        has_name = str(col).strip() != "" and str(col) != "nan"
        has_data = not df[col].isna().all()
        if has_name and has_data:
            columns_to_keep.append(col)

    if len(columns_to_keep) < len(df.columns):
        removed_count = len(df.columns) - len(columns_to_keep)
        logger.info(f"Removed {removed_count} empty column(s) from CSV file")

    df = df[columns_to_keep]

    # Fill remaining NaN to maintain consistency
    df = df.fillna(0.0)
    return df


def load_and_process_tdms_file(file_name):
    """Load TDMS file."""
    from nptdms import TdmsFile

    with TdmsFile.open(file_name) as tdms_file:
        # Get all groups in the file
        groups = tdms_file.groups()

        # Create a dictionary to store data from all groups
        data_dict = {}

        for group in groups:
            for channel in group.channels():
                channel_name = f"{group.name}/{channel.name}"
                data = channel[:]
                data_dict[channel_name] = data

        # Find the maximum length of data
        max_length = max(len(data) for data in data_dict.values())

        # Pad shorter arrays with NaN
        for key in data_dict:
            if len(data_dict[key]) < max_length:
                pad_length = max_length - len(data_dict[key])
                data_dict[key] = np.pad(
                    data_dict[key], (0, pad_length), "constant", constant_values=np.nan
                )

        # Create DataFrame
        df = pd.DataFrame(data_dict)

        # Remove empty columns (all NaN) to match training behavior
        columns_to_keep = []
        for col in df.columns:
            has_name = str(col).strip() != ""
            has_data = not df[col].isna().all()
            if has_name and has_data:
                columns_to_keep.append(col)

        if len(columns_to_keep) < len(df.columns):
            removed_count = len(df.columns) - len(columns_to_keep)
            logger.info(f"Removed {removed_count} empty column(s) from TDMS file")

        df = df[columns_to_keep]

        df = df.fillna(0.0)
        return df


def convert_asc_to_parquet(
    asc_path: Path, parquet_path: Optional[Path] = None, preserve_asc: bool = True
) -> Path:
    """Convert an ASC file to Parquet format with consistent column structure.

    Args:
        asc_path: Path to the ASC file
        parquet_path: Optional output path. If None, uses same name with .parquet extension
        preserve_asc: If True, keeps the original ASC file. If False, deletes it.

    Returns:
        Path to the created parquet file

    Note:
        This function ensures that the Parquet file has the EXACT same columns
        as the ASC file to prevent dimension mismatches in model training.
    """
    if parquet_path is None:
        parquet_path = asc_path.with_suffix(".parquet")

    # Load ASC file with careful column handling
    df = load_and_process_asc_file(str(asc_path))

    # Log column information for debugging
    logger.info(f"Converting {asc_path.name} to Parquet")
    logger.info(f"DataFrame shape: {df.shape}")
    logger.info(f"Columns ({len(df.columns)}): {df.columns.tolist()}")

    # CRITICAL: Verify no duplicate columns before saving
    if df.columns.duplicated().any():
        duplicates = df.columns[df.columns.duplicated()].tolist()
        logger.warning(f"Found duplicate columns: {duplicates}")
        logger.warning("This should not happen - column renaming failed!")
        raise ValueError(f"Duplicate columns detected: {duplicates}")

    # Convert to Parquet with compression
    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

    # Verify the conversion
    verify_df = pd.read_parquet(parquet_path)
    logger.info(f"Verification - Parquet shape: {verify_df.shape}")

    if df.shape != verify_df.shape:
        logger.error(f"SHAPE MISMATCH! ASC: {df.shape}, Parquet: {verify_df.shape}")
        raise ValueError(
            f"Column count mismatch after conversion! "
            f"Original: {df.shape[1]}, Parquet: {verify_df.shape[1]}"
        )

    # Optionally delete the ASC file to save space
    if not preserve_asc:
        try:
            asc_path.unlink()
            logger.info(f"Deleted original ASC file: {asc_path.name}")
        except Exception as e:
            logger.warning(f"Could not delete ASC file: {e}")

    logger.info(f"✓ Successfully converted {asc_path.name} to {parquet_path.name}")
    logger.info(f"✓ Column count preserved: {df.shape[1]} columns")

    return parquet_path


def verify_file_compatibility(file1_path: Path, file2_path: Path) -> bool:
    """Check if two files have compatible column structures.

    Args:
        file1_path: Path to first file
        file2_path: Path to second file

    Returns:
        True if files have same columns, False otherwise
    """
    try:
        # Load both files
        ext1 = file1_path.suffix.lower()
        ext2 = file2_path.suffix.lower()

        if ext1 == ".parquet":
            df1 = pd.read_parquet(file1_path)
        elif ext1 == ".csv":
            df1 = load_and_process_csv_file(str(file1_path))
        elif ext1 == ".asc":
            df1 = load_and_process_asc_file(str(file1_path))
        else:
            return False

        if ext2 == ".parquet":
            df2 = pd.read_parquet(file2_path)
        elif ext2 == ".csv":
            df2 = load_and_process_csv_file(str(file2_path))
        elif ext2 == ".asc":
            df2 = load_and_process_asc_file(str(file2_path))
        else:
            return False

        # Check column counts
        if df1.shape[1] != df2.shape[1]:
            logger.warning(
                f"Column count mismatch: {file1_path.name} has {df1.shape[1]} columns, "
                f"{file2_path.name} has {df2.shape[1]} columns"
            )
            return False

        # Check column names
        if not df1.columns.equals(df2.columns):
            logger.warning(
                f"Column names don't match between {file1_path.name} and {file2_path.name}"
            )
            logger.info(f"File 1 columns: {df1.columns.tolist()}")
            logger.info(f"File 2 columns: {df2.columns.tolist()}")
            return False

        logger.info(f"✓ Files are compatible: both have {df1.shape[1]} columns")
        return True

    except Exception as e:
        logger.error(f"Error checking compatibility: {e}")
        return False


def get_numeric_columns(file_path: Path) -> list:
    """Get list of numeric column names from a file.

    Args:
        file_path: Path to the file

    Returns:
        List of numeric column names
    """
    ext = file_path.suffix.lower()

    if ext == ".parquet":
        df = pd.read_parquet(file_path)
    elif ext == ".csv":
        df = load_and_process_csv_file(str(file_path))
    elif ext == ".asc":
        df = load_and_process_asc_file(str(file_path))
    else:
        return []

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    logger.info(f"Found {len(numeric_cols)} numeric columns in {file_path.name}")

    return numeric_cols
