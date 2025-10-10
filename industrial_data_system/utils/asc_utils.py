import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from nptdms import TdmsFile
import logging
import io
import chardet

import re

def load_and_process_asc_file(file_name):
    content = ""
    try:
        # Detect file encoding
        with open(file_name, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        file_encoding = result['encoding']

        # Try to read the file with the detected encoding
        try:
            with open(file_name, 'r', encoding=file_encoding) as file:
                content = file.read()
        except UnicodeDecodeError:
            # If that fails, try with 'latin-1' encoding
            with open(file_name, 'r', encoding='latin-1') as file:
                content = file.read()

        lines = content.split('\n')

        # Find the start of the data
        data_start = 0
        for i, line in enumerate(lines):
            # Check if the line contains tab-separated values and starts with a number-like string
            if '\t' in line and re.match(r'^[\d,.]+\t', line.strip()):
                data_start = i
                break

        if data_start == 0:
            raise ValueError("Could not find the start of data in the file.")

        # Extract header and data
        header = lines[data_start - 1].split('\t')
        data = [line.split('\t') for line in lines[data_start:] if line.strip()]

        # Ensure all data rows have the same number of columns as the header
        max_columns = len(header)
        data = [row for row in data if len(row) == max_columns]

        # Rename duplicate columns
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
            df[col] = df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            df[col] = pd.to_numeric(df[col], errors='coerce')

        logging.info(f"Successfully loaded ASC file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")
        return df

    except Exception as e:
        logging.error(f"Error loading ASC file: {str(e)}")
        if content:
            logging.error(f"File content (first 10 lines): {content.split('\n')[:10]}")
        else:
            logging.error("Unable to read file content")
        raise

def load_and_process_csv_file(file_name):
    return pd.read_csv(file_name)

def load_and_process_tdms_file(file_name):
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
            data_dict[key] = np.pad(data_dict[key], (0, pad_length), 'constant', constant_values=np.nan)

    # Create DataFrame
    df = pd.DataFrame(data_dict)
    return df