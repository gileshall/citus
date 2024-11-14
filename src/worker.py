import argparse
import logging
import multiprocessing
import queue
import time
import colorama
from doi import resolve_doi
import rxiv
import os
from traceback import format_exc
from persist import PersistentDict
from datetime import datetime

colorama.init()
logger = logging.getLogger(__name__)

# Setting up colored logging
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': colorama.Fore.CYAN + colorama.Back.BLACK,
        'INFO': colorama.Fore.GREEN + colorama.Back.BLACK,
        'WARNING': colorama.Fore.YELLOW + colorama.Back.BLACK,
        'ERROR': colorama.Fore.RED + colorama.Back.BLACK,
        'CRITICAL': colorama.Fore.WHITE + colorama.Back.RED,
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, colorama.Fore.WHITE)
        msg = super().format(record)
        return f"{level_color}{msg}{colorama.Style.RESET_ALL}"

# Setup colored logger for console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# Setup logger for file output (without colors)
file_handler = logging.FileHandler('process_dois.log')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)

class DOIWorker(multiprocessing.Process):
    def __init__(self, doi_queue, running_event, cache_path):
        super().__init__()
        self.doi_queue = doi_queue
        self.running_event = running_event
        self.cache_path = cache_path

    def run(self):
        logger.info(f"⭐ Worker {self.name} has started!")
        while self.running_event.is_set():
            try:
                doi = self.doi_queue.get(timeout=1)  # Get DOI from the queue with a timeout
                logger.info(f"🔍 Worker {self.name} got DOI: {doi}")
                
                # Run DOI processing in a separate process
                process = multiprocessing.Process(target=self.process_doi, args=(doi,))
                process.start()
                while process.is_alive():
                    process.join(timeout=0.5)
                    if not self.running_event.is_set():
                        logger.warning(f"🛑 Worker {self.name} stopping process for DOI: {doi} due to system stop signal...")
                        process.terminate()
                        process.join()
                        break

                if process.exitcode == 0:
                    logger.info(f"✅ Worker {self.name} finished processing DOI: {doi}")
                else:
                    logger.error(f"❌ Worker {self.name} failed to process DOI: {doi}")

                self.doi_queue.task_done()
            except queue.Empty:
                if not self.running_event.is_set():
                    logger.info(f"🚯 Worker {self.name} stopping due to system stop signal...")
                    break

    def process_doi(self, doi):
        try:
            doi_obj = resolve_doi(doi, cache_path=self.cache_path)
            text_path = doi_obj.analyze_article()
        except Exception as e:
            logger.error(f"An error occurred while processing DOI {doi}: {e}\n{format_exc()}")


def run_workers(doi_queue, num_workers, running_event, cache_path):
    workers = []
    for _ in range(num_workers):
        worker = DOIWorker(doi_queue, running_event, cache_path)
        worker.start()
        workers.append(worker)
    return workers


def process_dois(query, num_workers, start_date, end_date, interval, cache_path):
    doi_queue = multiprocessing.JoinableQueue()
    running_event = multiprocessing.Event()
    running_event.set()

    # Start the worker processes
    workers = run_workers(doi_queue, num_workers, running_event, cache_path)
    
    # Ensure cache directory exists
    queries_path = os.path.join(cache_path, "queries")
    os.makedirs(queries_path, exist_ok=True)
    
    # Fetch DOIs using rxiv module
    logger.info(f"🔎 Searching for DOIs with query: {query} from {start_date} to {end_date}...")
    search_cache_path = os.path.join(queries_path, f"__cache__{query}_{interval}.json")
    search_cache = PersistentDict(search_cache_path)
    
    for (start, end) in rxiv.date_range_iterator(start_date=start_date, end_date=end_date, interval=interval):
        key = f"{start},{end}"
        if key not in search_cache:
            logger.info(f"Searching from Start Date: {start} to End Date: {end}")
            try:
                dois = list(rxiv.search_biorxiv_and_extract_dois(query, limit_from=start, limit_to=end))
                search_cache[key] = dois
            except Exception as e:
                logger.error(f"An error occurred while fetching DOIs: {e}\n{format_exc()}")
                continue
        else:
            dois = search_cache[key]

        for doi in dois:
            doi_queue.put(doi)
            logger.info(f"🛥 DOI added: {doi}")

    try:
        doi_queue.join()  # Block until all tasks are done
    finally:
        # Ensure all workers finish processing
        logger.info("✅ Stopping all workers...")
        running_event.clear()  # Signal all workers to stop
        for worker in workers:
            worker.join()
        logger.info("✅ All workers have been stopped.")


def main():
    parser = argparse.ArgumentParser(description="Process DOIs with multiple workers.")
    parser.add_argument('--query', type=str, required=True, help='Search query term.')
    parser.add_argument('--num_workers', type=int, required=True, help='Number of worker processes to spawn.')
    parser.add_argument('--start_date', type=str, default='1970-01-01', help='Start date in YYYY-MM-DD format (default: %(default)s).')
    parser.add_argument('--end_date', type=str, default=datetime.today().strftime('%Y-%m-%d'), help='End date in YYYY-MM-DD format (default: %(default)s).')
    parser.add_argument('--interval', type=int, help='Interval in days for splitting the date range (default: entire range).')
    parser.add_argument('--cache_path', type=str, default='./doi-cache', help='Path to store DOI cache (default: %(default)s).')
    args = parser.parse_args()

    # Ensure cache directory exists
    os.makedirs(args.cache_path, exist_ok=True)

    try:
        process_dois(args.query, args.num_workers, args.start_date, args.end_date, args.interval, args.cache_path)
    except KeyboardInterrupt:
        logger.warning("🚯 Process interrupted by user.")
    finally:
        logger.info("👋 Exiting the program.")

if __name__ == '__main__':
    main()
