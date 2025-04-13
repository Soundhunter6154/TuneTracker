#!/usr/bin/env python3
import os
import random
import subprocess
import argparse

def get_duration(file_path):
    """
    Uses ffprobe to retrieve the duration (in seconds) of the audio file.
    This is crucial to ensure our splice is within the song's duration.
    """
    try:
        # Construct the ffprobe command:
        # -v error: only show errors
        # -show_entries format=duration: output only the duration field
        # -of default=noprint_wrappers=1:nokey=1: simplify the output format
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return float(output.strip())
    except Exception as e:
        raise RuntimeError(f"Failed to get duration for {file_path}: {e}")

def splice_audio(file_path, output_path, start, splice_duration):
    """
    Calls ffmpeg to extract a segment starting at 'start' with a duration of 'splice_duration' seconds.
    The -c copy flag is used to avoid re-encoding (which is fast) but note that
    it might not be frame-accurate if the start time isn’t on a keyframe.
    """
    try:
        # The command list avoids problems with special characters in file names.
        cmd = [
            'ffmpeg', '-y',          # -y: overwrite output files without asking
            '-ss', str(start),       # seek to the start time
            '-i', file_path,         # input file (handle special characters by passing as a list element)
            '-t', str(splice_duration),  # duration of the splice
            '-c', 'copy',            # copy codec (no re-encoding)
            output_path
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed for {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Splice random sections from audio files using ffmpeg."
    )
    parser.add_argument("input_dir", help="Directory containing audio files.")
    parser.add_argument("output_dir", help="Directory to save spliced clips.")
    parser.add_argument("--min_duration", type=float, default=5.0,
                        help="Minimum splice duration in seconds (default: 5.0).")
    parser.add_argument("--max_duration", type=float, default=30.0,
                        help="Maximum splice duration in seconds (default: 30.0).")
    parser.add_argument("--slices_per_file", type=int, default=1,
                        help="Number of random slices to extract from each file (default: 1).")
    args = parser.parse_args()

    # Create output directory if it doesn't exist.
    os.makedirs(args.output_dir, exist_ok=True)

    # Iterate over each file in the input directory.
    for filename in os.listdir(args.input_dir):
        input_path = os.path.join(args.input_dir, filename)
        
        # Skip non-files (like subdirectories)
        if not os.path.isfile(input_path):
            continue

        try:
            total_duration = get_duration(input_path)
        except RuntimeError as e:
            print(e)
            continue

        # Skip files that are too short to extract the minimum splice duration.
        if total_duration < args.min_duration:
            print(f"Skipping {filename}: duration ({total_duration:.2f}s) is less than the minimum splice duration.")
            continue

        # Split the filename into base and extension (to help generate output names).
        file_base, file_ext = os.path.splitext(filename)

        for i in range(args.slices_per_file):
            # Ensure we don't try to extract more than the file's length.
            max_possible_duration = min(args.max_duration, total_duration)
            
            # Randomly choose a splice duration between the specified minimum and maximum.
            splice_duration = random.uniform(args.min_duration, max_possible_duration)
            
            # Randomly choose a start time ensuring the splice stays within the file duration.
            max_start = total_duration - splice_duration
            start_time = random.uniform(0, max_start)
            
            # Construct an output filename that indicates it's a spliced clip.
            output_filename = f"{file_base}_slice{i}{file_ext}"
            output_path = os.path.join(args.output_dir, output_filename)
            
            try:
                splice_audio(input_path, output_path, start_time, splice_duration)
                print(f"Spliced '{filename}' -> '{output_filename}' (Start: {start_time:.2f}s, Duration: {splice_duration:.2f}s)")
            except RuntimeError as e:
                print(e)

if __name__ == "__main__":
    main()
