import pandas as pd
import chardet
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)


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


def convert_asc_to_csv(asc_file_path, csv_file_path=None):
    """
    Convert ASC file to CSV format.

    Parameters:
    -----------
    asc_file_path : str
        Path to the input ASC file
    csv_file_path : str, optional
        Path to the output CSV file. If not provided, will use the same name
        as the ASC file with .csv extension
    """
    # Load the ASC file
    df = load_and_process_asc_file(asc_file_path)

    # Generate output filename if not provided
    if csv_file_path is None:
        csv_file_path = asc_file_path.rsplit('.', 1)[0] + '.csv'

    # Save to CSV
    df.to_csv(csv_file_path, index=False)
    logging.info(f"Successfully converted {asc_file_path} to {csv_file_path}")

    return csv_file_path


# Example usage:
if __name__ == "__main__":
    # Replace with your actual file path
    input_file = "A:/TB/Versuch/5.2 Versuchsberichte Protokolle/2025/V24-2025 V60N-110 ohne Pumpenlecköl/V24-2025__0009.ASC"
    output_file = "data/V24-2025__0009.csv"  # Optional - will auto-generate if not provided

    try:
        convert_asc_to_csv(input_file, output_file)
        print(f"Conversion complete! CSV saved to: {output_file}")
    except Exception as e:
        print(f"Conversion failed: {str(e)}")