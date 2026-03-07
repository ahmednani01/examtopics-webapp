import re
from typing import List, Optional, Dict


class ContentParser:
    @staticmethod
    def parse_question_page(text: str) -> Dict:
        """Parse raw page text to extract MCQ content."""
        result = {
            "question": "",
            "options": [],
            "correct_answer": None,
            "explanation": "",
            "discussions": []
        }
        
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        question_pattern = r'(?:Topic|Question)\s*#:\s*\d+\s*\n\s*(.+?)\n\s*[A-D]\.'
        question_match = re.search(question_pattern, text, re.DOTALL | re.IGNORECASE)
        if question_match:
            question_text = question_match.group(1).strip()
            question_text = re.sub(r'^\s*[-–—]\s*', '', question_text)
            question_text = re.sub(r'^(Topic|Question)\s*#:\s*\d+\s*', '', question_text, flags=re.IGNORECASE)
            result["question"] = question_text
        
        options = []
        lines = text.split('\n')
        current_option = None
        current_text = []
        
        for line in lines:
            stripped = line.strip()
            if 'Suggested Answer' in stripped:
                if current_option:
                    options.append({
                        "letter": current_option,
                        "text": ' '.join(current_text).strip()
                    })
                break
            opt_match = re.match(r'^([A-D])\.\s*(.*)$', stripped)
            if opt_match:
                if current_option:
                    options.append({
                        "letter": current_option,
                        "text": ' '.join(current_text).strip()
                    })
                current_option = opt_match.group(1)
                current_text = [opt_match.group(2)] if opt_match.group(2) else []
            elif current_option and stripped:
                current_text.append(stripped)
        
        if current_option and (not options or options[-1]["letter"] != current_option):
            options.append({
                "letter": current_option,
                "text": ' '.join(current_text).strip()
            })
        
        result["options"] = options
        
        suggested_match = re.search(r'Suggested Answer:\s*([A-D])', text, re.IGNORECASE)
        if suggested_match:
            result["correct_answer"] = suggested_match.group(1).upper()
        
        discussions = ContentParser._extract_discussions(text)
        result["discussions"] = discussions
        
        return result
    
    @staticmethod
    def _extract_discussions(text: str) -> List[Dict]:
        """Extract discussions/comments from the page text."""
        discussions = []
        
        # Find the Comments section
        comments_start = text.find('Comments')
        if comments_start == -1:
            return discussions
        
        comments_text = text[comments_start:]
        
        # Remove "Load full discussion" and anything after
        load_full_pos = comments_text.find('Load full discussion')
        if load_full_pos > 0:
            comments_text = comments_text[:load_full_pos]
        
        # Split into blocks - discussions are typically separated by multiple newlines
        blocks = re.split(r'\n\s*\n\s*\n', comments_text)
        
        for block in blocks:
            if 'Selected Answer:' not in block:
                continue
            
            # Extract selected answer
            answer_match = re.search(r'Selected Answer:\s*([A-D])', block, re.IGNORECASE)
            if not answer_match:
                continue
            selected_answer = answer_match.group(1).upper()
            
            # Extract username - first word in the block that's a valid username
            words = block.strip().split()
            username = None
            for word in words[:5]:
                # Skip common UI words and look for username pattern
                if re.match(r'^[a-zA-Z0-9_]+$', word) and word.lower() not in ['comments', 'submit', 'cancel', 'new', 'switch', 'chosen', 'selected', 'answer']:
                    username = word
                    break
            
            if not username:
                continue
            
            # Extract timestamp
            ts_match = re.search(r'(\d+\s*(?:year|month|day|hour|minute)s?\s*,?\s*\d*\s*(?:a\.m\.|p\.m\.)?)', block, re.IGNORECASE)
            timestamp = ts_match.group(1) if ts_match else ""
            
            # Extract votes
            votes_match = re.search(r'upvoted\s*(\d+)\s*times?', block, re.IGNORECASE)
            votes = int(votes_match.group(1)) if votes_match else 0
            
            # Extract comment - after "Selected Answer: X" until "upvoted" or end
            comment_match = re.search(r'Selected Answer:\s*[A-D]\s*\n\s*(.+?)(?:\n\s*upvoted|\n\s*$)', block, re.DOTALL | re.IGNORECASE)
            if not comment_match:
                # Try alternative pattern - comment might be on same line or multiple lines
                comment_match = re.search(r'Selected Answer:\s*[A-D]\s*\n\s*(.+?)(?:upvoted|$)', block, re.DOTALL | re.IGNORECASE)
            if comment_match:
                comment_text = comment_match.group(1).strip()
                comment_text = re.sub(r'\s+', ' ', comment_text)
                
                if comment_text and len(comment_text) > 2:
                    discussions.append({
                        "user": username,
                        "comment": comment_text,
                        "votes": votes,
                        "selected_answer": selected_answer,
                        "timestamp": timestamp
                    })
        
        return discussions
    
    @staticmethod
    def extract_answer_from_html(text: str) -> Optional[str]:
        """Try to extract the correct answer from HTML-like text."""
        patterns = [
            r'Suggested Answer:\s*([A-D])',
            r'correct.*?([A-D])',
            r'right.*?answer.*?([A-D])',
            r'answer.*?(?:is|is:)\s*([A-D])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
