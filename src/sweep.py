import os
import json
import pandas as pd
import argparse
from datetime import datetime

def get_command_line_arguments():
    parser = argparse.ArgumentParser(description='Consolidate JSON analysis files into a TSV or JSON file.')
    parser.add_argument('-p', '--path', type=str, default='./doi-cache', help='Path to the directory containing JSON files (default: ./doi-cache)')
    parser.add_argument('-o', '--output', type=str, default='consolidated_analysis_data.tsv', help='Output file name (default: consolidated_analysis_data.tsv)')
    parser.add_argument('-f', '--format', type=str, choices=['tsv', 'json'], default='tsv', help='Output file format: tsv or json (default: tsv)')
    return parser.parse_args()

def collect_json_data(input_directory):
    data_list = []
    file_count = 0
    directory_count = 0

    # Walk through directory and subdirectories to find *_analysis.json files
    for root, dirs, files in os.walk(input_directory):
        directory_count += 1
        for file in files:
            if file.endswith("_analysis.json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as json_file:
                        data = json.load(json_file)

                        # Extract DOI from file path and add to the data
                        doi = extract_doi_from_path(file_path)
                        data['doi'] = doi

                        # Look for corresponding *_xref.json file
                        xref_file_path = file_path.replace("_analysis.json", "_xref.json")
                        if os.path.exists(xref_file_path):
                            with open(xref_file_path, 'r') as xref_file:
                                xref_data = json.load(xref_file)
                                data.update(extract_doi_metadata(xref_data))

                        data_list.append(data)
                        file_count += 1
                except json.JSONDecodeError as e:
                    print(f"Error reading {file_path}: {e}")
    return data_list, file_count, directory_count

def extract_doi_from_path(file_path):
    # Extract DOI from the path structure
    parts = file_path.split(os.sep)
    for part in parts:
        if part.startswith("10."):
            return part.replace('_', '/').replace('.json', '')
    return "NA"

def extract_doi_metadata(doi_metadata, default_value="NA"):
    extracted_data = {
        # Reference Count
        "reference_count": doi_metadata.get("reference-count", default_value),
        "is-referenced-by-count": doi_metadata.get("is-referenced-by-count", default_value),

        # Publisher Information
        "publisher": doi_metadata.get("publisher", default_value),
        "journal_title": doi_metadata.get("container-title", [default_value])[0] if doi_metadata.get("container-title", []) else default_value,

        # Funding Sources
        "funder_names": [funder.get("name", "Unknown funder") for funder in doi_metadata.get("funder", [])],
        "funder_awards": [award for funder in doi_metadata.get("funder", []) for award in funder.get("award", [])],
        "number_of_funders": len(doi_metadata.get("funder", [])),

        "author_count": len(doi_metadata.get("author", [])),

        # Boolean Fields
        "is_published_print": "published-print" in doi_metadata,
        "is_published_online": "published-online" in doi_metadata,

        # timestamp
        "_created_at": datetime.utcnow().isoformat()
    }

    return extracted_data

def create_dataframe(data_list):
    if not data_list:
        raise ValueError("No data found. Please ensure the directory contains valid *_analysis.json files.")

    # Create a Pandas DataFrame from the collected data
    df = pd.DataFrame(data_list)
    return df

def save_dataframe_to_tsv(df, output_file):
    # Save the consolidated data to a TSV file
    df.to_csv(output_file, sep='\t', index=False)

def save_data_to_json(data_list, output_file):
    # Save the consolidated data to a JSON file
    with open(output_file, 'w') as json_file:
        json.dump(data_list, json_file, indent=4)

def main():
    # Get command line arguments
    args = get_command_line_arguments()

    # Collect data from JSON files
    data_list, file_count, directory_count = collect_json_data(args.path)

    # Save data in the desired format
    if args.format == 'tsv':
        # Create a DataFrame from the collected data
        df = create_dataframe(data_list)
        # Save the DataFrame to a TSV file
        save_dataframe_to_tsv(df, args.output)
    elif args.format == 'json':
        # Save the data list to a JSON file
        save_data_to_json(data_list, args.output)

    # Print summary statistics
    print(f"Consolidated data saved to {args.output}")
    print(f"Number of directories visited: {directory_count}")
    print(f"Number of JSON files ingested: {file_count}")

if __name__ == "__main__":
    main()
