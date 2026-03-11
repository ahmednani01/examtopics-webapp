import httpx
from bs4 import BeautifulSoup
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
        self.client = httpx.Client(timeout=settings.request_timeout, headers=HEADERS)
    
    def close(self):
        self.client.close()
    
    def fetch_number_pages_for_provider(self, provider: str) -> int:
        """Fetch the number of pages for a provider's discussions."""
        url = f"https://www.examtopics.com/discussions/{provider}/"
        try:
            response = self.client.get(url)
            if response.status_code == 404:
                logger.error(f"Provider {provider} not found")
                raise Exception(f"Provider '{provider}' not found")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            element = soup.select_one("div:nth-of-type(2) > div > div:nth-of-type(1) > div > span > span:nth-of-type(1) > strong:nth-of-type(2)")
            if element:
                return int(element.text) + 1
            return 1
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch page count: {e}")
            raise
    
    def fetch_page(self, provider: str, page_number: int) -> List[Dict]:
        """Fetch question links from a specific page of a provider's discussions."""
        base_url = f"https://www.examtopics.com/discussions/{provider}/"
        url = f"{base_url}{page_number}" if page_number > 1 else base_url
        attempts = 0
        rows = []
        
        while attempts < settings.retry_attempts:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.select('div div div div div div div div h2 a')
                    
                    for link in links:
                        href = link.get('href', '')
                        title_match = link.text.strip()
                        
                        if 'exam-' not in href or 'topic' not in href or 'question' not in href:
                            continue
                        
                        try:
                            exam_part = href.split('exam-')[1].split('-topic')[0]
                            topic = int(href.split('topic-')[1].split('-question')[0])
                            question = int(href.split('question-')[1].split('-discussion')[0])
                            
                            rows.append({
                                'title': exam_part,
                                'topic': topic,
                                'number': question,
                                'link': f"https://www.examtopics.com{href}"
                            })
                        except (IndexError, ValueError):
                            continue
                    
                    logger.info(f'Page {page_number} Done for {provider}')
                    return rows
            except httpx.HTTPError:
                pass
            attempts += 1
            sleep(5)
        
        logger.error(f"Failed to fetch page {page_number} for {provider} after {settings.retry_attempts} attempts.")
        return rows
    
    def fetch_all_questions_for_provider(self, provider: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Fetch all question links for a provider (all exams)."""
        logger.info(f"Starting to process {provider}...")
        
        try:
            number_of_pages = self.fetch_number_pages_for_provider(provider)
            logger.info(f"Found {number_of_pages - 1} pages for {provider}...")
        except Exception as e:
            logger.error(f"Failed to fetch page count: {e}")
            return []
        
        all_rows = []
        total_pages = number_of_pages - 1
        
        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            futures = [executor.submit(self.fetch_page, provider, x) for x in range(1, number_of_pages)]
            completed = 0
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Scraping {provider}"):
                rows = future.result()
                if rows:
                    all_rows.extend(rows)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total_pages, len(all_rows))
        
        logger.info(f"Found {len(all_rows)} total questions for {provider}")
        return all_rows
    
    def fetch_all_questions(self, provider: str, exam_code: str, progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Fetch all question links for an exam."""
        all_rows = self.fetch_all_questions_for_provider(provider, progress_callback)
        
        filtered_rows = [row for row in all_rows if row['title'].lower() == exam_code.lower()]
        
        sorted_rows = sorted(filtered_rows, key=lambda x: (x['title'], int(x['number'])))
        
        for i, row in enumerate(sorted_rows, 1):
            row['id'] = i
        
        logger.info(f"Found {len(sorted_rows)} questions for {provider}/{exam_code}")
        return sorted_rows
    
    def fetch_providers(self) -> List[Dict]:
        """Fetch all certification providers from examtopics.com."""
        url = "https://www.examtopics.com/exams/"
        try:
            response = self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch providers: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            providers = []
            links = soup.select('.provider-list-link a')
            
            for link in links:
                href = link.get('href', '')
                if '/exams/' in href and href.count('/') == 3:
                    provider = href.strip('/').split('/')[-1]
                    text = link.text.strip()
                    exam_count = 0
                    if '(' in text and ')' in text:
                        try:
                            exam_count = int(text.split('(')[1].split(' ')[0])
                        except:
                            pass
                    providers.append({
                        'name': provider,
                        'display_name': text.split('(')[0].strip() if '(' in text else text,
                        'exam_count': exam_count
                    })
            
            logger.info(f"Found {len(providers)} providers")
            return providers
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch providers: {e}")
            return []

    def fetch_exams_for_provider(self, provider: str) -> List[Dict]:
        """Fetch all exams for a specific provider."""
        url = f"https://www.examtopics.com/exams/{provider}/"
        try:
            response = self.client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch exams for {provider}: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            exams = []
            links = soup.select('a.popular-exam-link')
            
            for link in links:
                href = link.get('href', '')
                exam_code = href.strip('/').split('/')[-1]
                
                text = link.text.strip()
                display_name = text.split(':')[0] if ':' in text else exam_code
                description = text.split(':')[1].strip() if ':' in text else ''
                
                exams.append({
                    'code': exam_code,
                    'provider': provider,
                    'exam_id': f"{provider}-{exam_code}",
                    'display_name': display_name,
                    'description': description
                })
            
            logger.info(f"Found {len(exams)} exams for {provider}")
            return exams
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch exams for {provider}: {e}")
            return []
