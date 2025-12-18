import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import chardet
import re
import logging
from typing import Tuple, Dict, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# ============================================================================
# STEP 1: Load ASC File
# ============================================================================

def load_and_process_asc_file(file_name: str) -> pd.DataFrame:
    """Load ASC or SC file and return DataFrame with consistent column structure.

    This function carefully preserves the original column structure to avoid
    dimension mismatches when loading into trained models.

    Note: .sc files are treated identically to .asc files.
    """
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
            df[col] = df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # CRITICAL: Fill NaN values with 0 to maintain consistent structure
        df = df.fillna(0.0)

        logging.info(f"Successfully loaded ASC file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")

        return df

    except Exception as e:
        logging.error(f"Error loading ASC file: {str(e)}")
        if content:
            logging.error(f"File content (first 10 lines): {content.split('\\n')[:10]}")
        else:
            logging.error("Unable to read file content")
        raise


# ============================================================================
# STEP 2: Extract Target Channels from DataFrame
# ============================================================================

def extract_pump_channels(
        df: pd.DataFrame,
        target_channels: Optional[List[str]] = None
) -> Dict[str, np.ndarray]:
    """
    Extract relevant pump channels from DataFrame.

    Args:
        df: DataFrame loaded from ASC file
        target_channels: List of column names to extract. If None, uses default channels.

    Returns:
        Dictionary mapping channel names to numpy arrays
    """

    print(f"{'=' * 70}")
    print(f"STEP 2: EXTRACTING PUMP CHANNELS")
    print(f"{'=' * 70}")

    # Default target channels (adjust these to match your ASC file columns)
    if target_channels is None:
        target_channels = [
            'Messzeit[s]',
            'Pressure [bar]',
            'Flow [L/min]',
            'Leak [L/min]',
            'Speed [rpm]',
            'Torque [Nm]',
            'LS [bar]',
            'Housing [bar]',
            'TempSaug [°C]',
            'TempLeak [°C]',
        ]

    print(f"Available columns in ASC file: {df.columns.tolist()}")
    print()
    print(f"Target channels: {target_channels}")
    print()

    # Extract channels (with fuzzy matching for flexibility)
    data = {}
    missing_channels = []

    for target in target_channels:
        # Try exact match first
        if target in df.columns:
            data[target] = df[target].values
            print(f"✓ Found: {target}")
        else:
            # Try fuzzy matching (case-insensitive, ignore spaces)
            normalized_target = target.lower().replace(' ', '').replace('[', '').replace(']', '')
            found = False

            for col in df.columns:
                normalized_col = col.lower().replace(' ', '').replace('[', '').replace(']', '')
                if normalized_target in normalized_col or normalized_col in normalized_target:
                    data[target] = df[col].values
                    print(f"✓ Found (fuzzy match): {target} → {col}")
                    found = True
                    break

            if not found:
                missing_channels.append(target)
                print(f"✗ Missing: {target}")

    if missing_channels:
        print()
        print(f"WARNING: {len(missing_channels)} channels not found in ASC file:")
        for ch in missing_channels:
            print(f"  - {ch}")
        print()
        print(f"Available columns to choose from:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

    print()
    print(f"Extracted {len(data)} channels with {len(df)} samples each")
    print()

    return data


# ============================================================================
# STEP 3: Calculate Sampling Rate from Time Column
# ============================================================================

def estimate_sampling_rate(time_array: np.ndarray) -> float:
    """
    Estimate sampling rate from time array.
    """

    print(f"{'=' * 70}")
    print(f"STEP 3: ESTIMATING SAMPLING RATE")
    print(f"{'=' * 70}")

    # Calculate time differences
    dt = np.diff(time_array)

    # Remove outliers (in case of missing samples)
    dt_median = np.median(dt)
    dt_clean = dt[np.abs(dt - dt_median) < 0.1 * dt_median]

    # Average sampling interval
    avg_dt = np.mean(dt_clean)
    sampling_rate = 1.0 / avg_dt

    print(f"Time array length: {len(time_array)}")
    print(f"Time range: [{time_array[0]:.4f}, {time_array[-1]:.4f}] s")
    print(f"Duration: {time_array[-1] - time_array[0]:.4f} s")
    print(f"Average sampling interval: {avg_dt:.6f} s")
    print(f"Estimated sampling rate: {sampling_rate:.2f} Hz")
    print(f"Sampling interval std: {np.std(dt_clean):.6f} s")
    print()

    return sampling_rate


# ============================================================================
# STEP 4: Windowed FFT Processing
# ============================================================================

def apply_windowed_fft(
        signal: np.ndarray,
        window_size: int,
        overlap: float,
        sampling_rate: float,
        channel_name: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Apply FFT with sliding windows to handle long time series.

    Args:
        signal: Input signal array
        window_size: Number of samples per window (should be power of 2)
        overlap: Overlap fraction (0.0 to 1.0), typically 0.5
        sampling_rate: Sampling rate in Hz
        channel_name: Name of the channel for logging

    Returns:
        freqs: Frequency bins
        fft_windows: FFT magnitude for each window (n_windows × n_freq_bins)
        fft_avg: Average FFT magnitude across all windows
    """

    print(f"{'=' * 70}")
    print(f"STEP 4: WINDOWED FFT - {channel_name}")
    print(f"{'=' * 70}")

    n_samples = len(signal)
    step_size = int(window_size * (1 - overlap))
    n_windows = (n_samples - window_size) // step_size + 1

    print(f"Signal length: {n_samples} samples")
    print(f"Window size: {window_size} samples ({window_size / sampling_rate:.3f} s)")
    print(f"Overlap: {overlap * 100:.0f}%")
    print(f"Step size: {step_size} samples")
    print(f"Number of windows: {n_windows}")
    print()

    # Prepare storage for FFT results
    n_freq_bins = window_size // 2 + 1
    fft_windows = np.zeros((n_windows, n_freq_bins))

    # Hann window for all segments
    window = np.hanning(window_size)

    # Process each window
    for i in range(n_windows):
        start_idx = i * step_size
        end_idx = start_idx + window_size

        # Extract window
        signal_window = signal[start_idx:end_idx]

        # Apply window function
        windowed_signal = signal_window * window

        # Compute FFT
        fft_complex = np.fft.rfft(windowed_signal)

        # Compute magnitude
        fft_magnitude = np.abs(fft_complex) / window_size
        fft_magnitude[1:-1] *= 2  # Account for negative frequencies

        fft_windows[i, :] = fft_magnitude

    # Average across all windows
    fft_avg = np.mean(fft_windows, axis=0)

    # Frequency bins
    freqs = np.fft.rfftfreq(window_size, 1 / sampling_rate)

    print(f"FFT computed for {n_windows} windows")
    print(f"Frequency bins: {len(freqs)}")
    print(f"Frequency resolution: {freqs[1] - freqs[0]:.4f} Hz")
    print(f"Max frequency: {freqs[-1]:.2f} Hz")
    print()

    # Find dominant frequencies
    top_indices = np.argsort(fft_avg)[-5:][::-1]
    print(f"Top 5 dominant frequencies (averaged):")
    for j, idx in enumerate(top_indices, 1):
        print(f"  {j}. Frequency: {freqs[idx]:7.2f} Hz, Magnitude: {fft_avg[idx]:.6f}")
    print()

    return freqs, fft_windows, fft_avg


# ============================================================================
# STEP 5: Select Relevant Frequency Range
# ============================================================================

def select_frequency_range(
        freqs: np.ndarray,
        magnitudes: np.ndarray,
        max_freq: float = 500.0,
        shaft_freq: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Keep only relevant frequency range for pump analysis.

    Args:
        freqs: Frequency bins
        magnitudes: FFT magnitudes (can be 1D or 2D)
        max_freq: Maximum frequency to keep
        shaft_freq: Shaft frequency for reference (optional)
    """

    print(f"{'=' * 70}")
    print(f"STEP 5: FREQUENCY RANGE SELECTION")
    print(f"{'=' * 70}")

    # Handle both 1D and 2D magnitude arrays
    is_2d = magnitudes.ndim == 2

    # Find indices within frequency range
    freq_mask = freqs <= max_freq
    selected_freqs = freqs[freq_mask]

    if is_2d:
        selected_magnitudes = magnitudes[:, freq_mask]
        print(f"Original shape: {magnitudes.shape} (windows × freq_bins)")
        print(f"Selected shape: {selected_magnitudes.shape}")
    else:
        selected_magnitudes = magnitudes[freq_mask]
        print(f"Original frequency bins: {len(freqs)}")
        print(f"Selected frequency bins: {len(selected_freqs)}")

    print(f"Frequency range: 0 - {max_freq} Hz")
    print(f"Selected frequency range: [0, {selected_freqs[-1]:.2f}] Hz")
    print(f"Reduction factor: {len(freqs) / len(selected_freqs):.2f}x")

    if shaft_freq is not None:
        print(f"Shaft frequency: {shaft_freq:.2f} Hz")
        print(f"Harmonics included: {int(max_freq / shaft_freq)}")

    print()

    return selected_freqs, selected_magnitudes


# ============================================================================
# STEP 6: Process All Channels
# ============================================================================

def process_all_channels_from_asc(
        data: Dict[str, np.ndarray],
        window_size: int = 1024,
        overlap: float = 0.5,
        max_freq: float = 500.0,
) -> Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]:
    """
    Apply FFT to all channels from ASC data.

    Returns:
        freqs: Frequency bins
        fft_features: Dictionary of averaged FFT magnitudes per channel
        feature_matrix: Stacked feature matrix (freq_bins × n_channels)
    """

    print(f"{'=' * 70}")
    print(f"STEP 6: MULTI-CHANNEL FFT PROCESSING")
    print(f"{'=' * 70}")

    # Extract time column and calculate sampling rate
    if 'Messzeit[s]' in data:
        time_array = data['Messzeit[s]']
        sampling_rate = estimate_sampling_rate(time_array)
        channel_names = [k for k in data.keys() if k != 'Messzeit[s]']
    else:
        # Assume first column is time if 'Messzeit[s]' not found
        first_key = list(data.keys())[0]
        time_array = data[first_key]
        sampling_rate = estimate_sampling_rate(time_array)
        channel_names = list(data.keys())[1:]

    # Try to estimate shaft frequency from Speed column
    shaft_freq = None
    for key in data.keys():
        if 'speed' in key.lower() or 'rpm' in key.lower():
            avg_speed_rpm = np.mean(data[key])
            shaft_freq = avg_speed_rpm / 60.0
            print(f"Detected average shaft speed: {avg_speed_rpm:.1f} RPM ({shaft_freq:.2f} Hz)")
            break

    print(f"Processing {len(channel_names)} channels:")
    for i, name in enumerate(channel_names, 1):
        print(f"  {i}. {name}")
    print()

    # Process each channel
    fft_features = {}
    freqs = None

    for channel_name in channel_names:
        signal = data[channel_name]

        # Apply windowed FFT
        channel_freqs, fft_windows, fft_avg = apply_windowed_fft(
            signal, window_size, overlap, sampling_rate, channel_name
        )

        # Select frequency range
        selected_freqs, selected_avg = select_frequency_range(
            channel_freqs, fft_avg, max_freq, shaft_freq
        )

        fft_features[channel_name] = selected_avg

        if freqs is None:
            freqs = selected_freqs

        print(f"✓ Processed {channel_name}")
        print()

    # Stack features into matrix
    feature_matrix = np.column_stack([fft_features[name] for name in channel_names])

    print(f"{'=' * 70}")
    print(f"FINAL FEATURE MATRIX")
    print(f"{'=' * 70}")
    print(f"Shape: {feature_matrix.shape}")
    print(f"  Rows (frequency bins): {feature_matrix.shape[0]}")
    print(f"  Columns (channels): {feature_matrix.shape[1]}")
    print(f"Total features: {feature_matrix.size}")
    print(f"Feature vector dimension for autoencoder: {feature_matrix.size}")
    print()

    return freqs, fft_features, feature_matrix


# ============================================================================
# STEP 7: Visualize Results
# ============================================================================

def visualize_asc_fft_results(
        data: Dict[str, np.ndarray],
        freqs: np.ndarray,
        fft_features: Dict[str, np.ndarray],
        output_path: str = 'asc_fft_analysis.png',
):
    """
    Create visualization of time domain and frequency domain from ASC data.
    """

    print(f"{'=' * 70}")
    print(f"STEP 7: VISUALIZATION")
    print(f"{'=' * 70}")

    # Get time array
    time_key = 'Messzeit[s]' if 'Messzeit[s]' in data else list(data.keys())[0]
    t = data[time_key]

    # Select channels to plot (exclude time)
    channel_names = [k for k in data.keys() if k != time_key]
    channels_to_plot = channel_names[:3]  # Plot first 3 channels

    if len(channels_to_plot) == 0:
        print("No channels to plot!")
        return

    fig, axes = plt.subplots(len(channels_to_plot), 2, figsize=(15, 4 * len(channels_to_plot)))

    if len(channels_to_plot) == 1:
        axes = axes.reshape(1, -1)

    fig.suptitle('ASC File: Time Domain vs Frequency Domain Analysis',
                 fontsize=16, fontweight='bold')

    for i, channel in enumerate(channels_to_plot):
        # Time domain plot (show first 2 seconds)
        ax_time = axes[i, 0]
        sampling_rate = 1.0 / np.mean(np.diff(t))
        n_samples_to_plot = min(len(t), int(2 * sampling_rate))

        ax_time.plot(t[:n_samples_to_plot], data[channel][:n_samples_to_plot],
                     linewidth=0.8, color='steelblue')
        ax_time.set_xlabel('Time [s]', fontsize=10)
        ax_time.set_ylabel(channel, fontsize=10)
        ax_time.set_title(f'Time Domain - {channel}', fontsize=11, fontweight='bold')
        ax_time.grid(True, alpha=0.3)

        # Frequency domain plot
        ax_freq = axes[i, 1]
        ax_freq.plot(freqs, fft_features[channel], linewidth=1.0, color='darkred')
        ax_freq.set_xlabel('Frequency [Hz]', fontsize=10)
        ax_freq.set_ylabel('Magnitude', fontsize=10)
        ax_freq.set_title(f'Frequency Domain - {channel}', fontsize=11, fontweight='bold')
        ax_freq.grid(True, alpha=0.3)
        ax_freq.set_xlim([0, min(300, freqs[-1])])  # Focus on lower frequencies

        # Mark top peaks
        top_indices = np.argsort(fft_features[channel])[-3:][::-1]
        for idx in top_indices:
            ax_freq.plot(freqs[idx], fft_features[channel][idx], 'ro', markersize=6)
            ax_freq.annotate(f'{freqs[idx]:.1f} Hz',
                             xy=(freqs[idx], fft_features[channel][idx]),
                             xytext=(5, 5), textcoords='offset points',
                             fontsize=8, color='darkred')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_path}")
    print()


# ============================================================================
# MAIN TEST EXECUTION WITH ASC FILE
# ============================================================================

def main_asc_fft_test(asc_file_path: str):
    """
    Main function to process ASC file with FFT analysis.

    Args:
        asc_file_path: Path to the ASC file
    """

    print("\n" + "=" * 70)
    print(" " * 10 + "FFT PROCESSING WITH ASC FILE")
    print("=" * 70 + "\n")

    try:
        # Step 1: Load ASC file
        print(f"Loading ASC file: {asc_file_path}")
        df = load_and_process_asc_file(asc_file_path)

        # Step 2: Extract pump channels
        data = extract_pump_channels(df)

        if len(data) < 2:  # Need at least time + 1 channel
            raise ValueError("Insufficient channels extracted from ASC file")

        # Step 3-6: Process with FFT
        freqs, fft_features, feature_matrix = process_all_channels_from_asc(
            data,
            window_size=1024,  # Adjust based on your data
            overlap=0.5,
            max_freq=500.0
        )

        # Step 7: Visualize
        visualize_asc_fft_results(data, freqs, fft_features)

        # Summary
        print(f"{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"✓ Loaded ASC file: {df.shape[0]} samples, {df.shape[1]} columns")
        print(f"✓ Extracted {len(data) - 1} pump channels")
        print(f"✓ Applied windowed FFT to all channels")
        print(f"✓ Created feature matrix: {feature_matrix.shape}")
        print(f"✓ Frequency resolution: {freqs[1] - freqs[0]:.4f} Hz")
        print(f"✓ Frequency range: 0 - {freqs[-1]:.2f} Hz")
        print()
        print(f"AUTOENCODER INPUT DIMENSION: {feature_matrix.size}")
        print(f"  Option 1 - Single vector: Flatten to {feature_matrix.size} features")
        print(f"  Option 2 - Multiple samples: {feature_matrix.shape[0]} samples × {feature_matrix.shape[1]} features")
        print("=" * 70)

        return df, data, freqs, fft_features, feature_matrix

    except Exception as e:
        logging.error(f"Error in FFT processing: {str(e)}")
        raise


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Replace with your actual ASC file path
    asc_file_path = "Data/V24-2025__0011_2.ASC"

    # Run the complete FFT analysis
    df, data, freqs, fft_features, feature_matrix = main_asc_fft_test(asc_file_path)

    # Now you can use feature_matrix with your Autoencoder
    # Flatten for single-vector approach:
    flattened_features = feature_matrix.flatten()
    print(f"\nFlattened feature vector shape: {flattened_features.shape}")

    # Or use each frequency bin as a sample (recommended for autoencoder):
    print(f"Per-frequency feature shape: {feature_matrix.shape}")