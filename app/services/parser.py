import re
from typing import List, Optional, Dict


class ContentParser:

    @staticmethod
    def parse_question_page(text: str) -> Dict:
        result = {
            "question": "",
            "options": [],
            "correct_answer": None,
            "explanation": "",
            "discussions": []
        }

        # Normalize whitespace
        text = re.sub(r'\r', '', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # ------------------------
        # OPTIONS (check first to detect MCQ vs simulation)
        # ------------------------
        option_pattern = re.compile(
            r'\n\s*([A-Z])\.\s+(.*?)'
            r'(?=\n\s*[A-Z]\.\s+|\n\s*Suggested Answer|\Z)',
            re.DOTALL
        )

        options = []
        for letter, content in option_pattern.findall(text):
            content = re.sub(r'\s+', ' ', content).strip()
            content = re.sub(r'Most Voted', '', content)
            options.append({
                "letter": letter,
                "text": content
            })

        result["options"] = options

        # ------------------------
        # QUESTION
        # ------------------------
        is_simulation = len(options) == 0 or 'SIMULATION' in text[:500]

        if is_simulation:
            # Simulation question - extract after Topic #:
            q_match = re.search(
                r'Topic\s*#:\s*\d+\s*\n*\s*(.*?)(?=\n\s*Suggested Answer|\Z)',
                text,
                re.DOTALL | re.IGNORECASE
            )
            if q_match:
                question = q_match.group(1).strip()
                # Clean up - remove UI elements
                question = re.sub(r'Show Suggested Answer.*', '', question, flags=re.IGNORECASE)
                question = re.sub(r'Hide Answer.*', '', question, flags=re.IGNORECASE)
                question = re.sub(r'\s+', ' ', question).strip()
                result["question"] = question
        else:
            # MCQ question
            q_match = re.search(
                r'Topic\s*#:\s*\d+\s*\n*\s*(.*?)(?=\n\s*[A-Z]\.\s+|\Z)',
                text,
                re.DOTALL | re.IGNORECASE
            )
            if q_match:
                question = q_match.group(1).strip()
                question = re.sub(r'\s+', ' ', question)
                result["question"] = question

        # ------------------------
        # CORRECT ANSWER
        # ------------------------
        if not is_simulation:
            answer_match = re.search(
                r'Suggested Answer:\s*([A-Z]+)',
                text,
                re.IGNORECASE
            )
            if answer_match:
                result["correct_answer"] = answer_match.group(1).strip()

        # ------------------------
        # DISCUSSIONS
        # ------------------------
        result["discussions"] = ContentParser._extract_discussions(text)

        return result

    # ---------------------------------------------------

    @staticmethod
    def _extract_discussions(text: str) -> List[Dict]:

        discussions = []

        comment_pattern = re.compile(
            r'\n\s*([A-Za-z0-9_]+)\s*'
            r'(?:Highly Voted|Most Recent)?\s*'
            r'([\d\s\w,]+ago)\s*'
            r'Selected Answer:\s*([A-Z])\s*'
            r'(.*?)'
            r'upvoted\s*(\d+)\s*times?',
            re.DOTALL | re.IGNORECASE
        )

        for user, timestamp, answer, comment, votes in comment_pattern.findall(text):

            comment = re.sub(r'\s+', ' ', comment).strip()

            discussions.append({
                "user": user,
                "comment": comment,
                "votes": int(votes),
                "selected_answer": answer,
                "timestamp": timestamp.strip()
            })

        return discussions

    # ---------------------------------------------------

    @staticmethod
    def extract_answer_from_html(text: str) -> Optional[str]:

        patterns = [
            r'Suggested Answer:\s*([A-Z]+)',
            r'correct.*?([A-Z])',
            r'right.*?answer.*?([A-Z])',
            r'answer.*?(?:is|is:)\s*([A-Z])',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None
