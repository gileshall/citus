![citus logo](https://raw.githubusercontent.com/gileshall/citus/refs/heads/main/media/citus.jpg)

This repository contains tools and methodologies for analyzing scientific articles, specifically focusing on those related to genomic analysis and bioinformatics. The main objective is to assess the usage of tools like the Genome Analysis Toolkit (GATK), Picard, Integrative Genomics Viewer (IGV), and HTSJDK within the context of scientific publications. 

By leveraging natural language processing and detailed analyses, the project extracts relevant information from research papers, categorizes methodologies, and evaluates scientific impact to support further research and development.

## Features

- **Tool Relevance Evaluation**: Automatically determines if tools like GATK, Picard, IGV, and HTSJDK are mentioned or utilized in the analysis.
- **Scientific Impact Assessment**: Rates the impact of research articles on a scale of 1 to 5.
- **Methodological Detailing**: Extracts and summarizes methodologies used in research.
- **Comparative Tool Analysis**: Compares the mentioned tools against others and summarizes results.
- **Structured JSON Output**: Produces a well-structured JSON for further statistical analysis.

## Installation

To get started, clone the repository and install the necessary dependencies.

```bash
git clone https://github.com/yourusername/repo-name.git
cd repo-name
pip install -r requirements.txt
```

Make sure you have Python 3.7 or higher installed.

## Usage

To analyze a scientific article using the provided tools, you can run the `src/worker.py` script from the command line, providing the DOI of the article and other optional parameters. 

```bash
python src/worker.py <DOI> [--other-parameters]
```

## Command-Line Options

```
usage: worker.py [-h] [--num_workers NUM_WORKERS] [--start_date START_DATE]
               [--end_date END_DATE] [--interval INTERVAL] [--cache_path CACHE_PATH]
               query

Search BioRxiv for articles and extract DOIs.

positional arguments:
  query                 Search query term.

optional arguments:
  -h, --help            show this help message and exit
  --num_workers NUM_WORKERS
                        Number of worker processes to spawn.
  --start_date START_DATE
                        Start date in YYYY-MM-DD format (default: 1970-01-01).
  --end_date END_DATE   End date in YYYY-MM-DD format (default: today).
  --interval INTERVAL    Interval in days for splitting the date range.
  --cache_path CACHE_PATH
                        Path to store DOI cache (default: ./doi-cache).
```

## Output

The analysis will generate structured JSON files describing the findings based on the functionalities listed. This includes tool relevance, methodological details, comparison summaries, and other metrics relevant to the scientific article being analyzed.

Example of output JSON:

```json
{
  "gatk_related": true,
  "scientific_impact": 4,
  "methodological_details": ["Variant calling", "Quality control"],
  "results_summary_gatk": "Positive",
  ...
}
```
