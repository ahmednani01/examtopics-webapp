import requests
from time import sleep
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'fr,fr-FR;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
    'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


class ExamScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def fetch_number_pages(self, exam: str) -> int:
        """Fetch the number of pages for an exam."""
        base_url = f"https://www.examtopics.com/discussions/{exam}/"
        try:
            response = self.session.get(base_url, timeout=settings.request_timeout)
            if response.status_code == 404:
                logger.error(f"{exam} not found")
                raise Exception(f"Exam '{exam}' not found")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            element = soup.select_one("div:nth-of-type(2) > div > div:nth-of-type(1) > div > span > span:nth-of-type(1) > strong:nth-of-type(2)")
            if element:
                return int(element.text) + 1
            return 1
        except requests.RequestException as e:
            logger.error(f"Failed to fetch page count: {e}")
            raise
    
    def fetch_page(self, exam: str, page_number: int) -> List[Dict]:
        """Fetch question links from a specific page."""
        base_url = f"https://www.examtopics.com/discussions/{exam}/"
        url = f"{base_url}{page_number}"
        attempts = 0
        rows = []
        
        while attempts < settings.retry_attempts:
            try:
                response = self.session.get(url, timeout=settings.request_timeout)
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.select('div div div div div div div div h2 a')
                    
                    for link in links:
                        title = link.text.strip()[5:].split(' topic')[0]
                        topic = int(link.text.strip().split('topic ')[1].split(' question')[0])
                        question = int(link.text.strip().split('question ')[1].split(' discussion')[0])
                        rows.append({
                            'title': title,
                            'topic': topic,
                            'number': question,
                            'link': f"https://www.examtopics.com{link.get('href')}"
                        })
                    logger.info(f'Page {page_number} Done for {exam.upper()}')
                    return rows
            except requests.RequestException:
                pass
            attempts += 1
            sleep(5)
        
        logger.error(f"Failed to fetch page {page_number} for {exam} after {settings.retry_attempts} attempts.")
        return rows
    
    def fetch_all_questions(self, exam: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Fetch all question links for an exam."""
        logger.info(f"Starting to process {exam.upper()}...")
        
        try:
            number_of_pages = self.fetch_number_pages(exam)
            logger.info(f"Found {number_of_pages - 1} pages for {exam.upper()}...")
        except Exception as e:
            logger.error(f"Failed to fetch page count: {e}")
            return []
        
        all_rows = []
        total_pages = number_of_pages - 1
        
        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            futures = [executor.submit(self.fetch_page, exam, x) for x in range(1, number_of_pages)]
            completed = 0
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Scraping {exam.upper()}"):
                rows = future.result()
                if rows:
                    all_rows.extend(rows)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_pages, len(all_rows))
        
        sorted_rows = sorted(all_rows, key=lambda x: (x['title'], int(x['number'])))
        
        for i, row in enumerate(sorted_rows, 1):
            row['id'] = i
        
        logger.info(f"Found {len(sorted_rows)} questions for {exam.upper()}")
        return sorted_rows
    
    def get_exam_list(self) -> List[str]:
        """Return a list of common exam providers."""
        return [
            "microsoft",
            "amazon",
            "google",
            "cncf",
            "hashicorp",
            "cisco",
            "compTIA",
        ]
