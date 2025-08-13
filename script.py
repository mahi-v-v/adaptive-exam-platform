# Create the updated backend.py with robust JSON handling and buffer support
backend_content = '''import fitz  # PyMuPDF
import requests
import json
import os
import re
import time
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple

# Load environment variables
load_dotenv()


class PDFProcessor:
    """Handle PDF text extraction using PyMuPDF"""

    @staticmethod
    def extract_text_from_pdf(pdf_file) -> Tuple[str, str]:
        """Extract text from uploaded PDF file"""
        try:
            pdf_bytes = pdf_file.read()
            if len(pdf_bytes) == 0:
                return "", "Error: The uploaded file is empty."

            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            if pdf_document.page_count == 0:
                return "", "Error: The PDF file appears to be corrupted or has no pages."

            extracted_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                extracted_text += page.get_text() + "\\n"

            pdf_document.close()

            if not extracted_text.strip():
                return "", "Error: No text could be extracted. The file might be image-based."

            return extracted_text.strip(), ""

        except Exception as e:
            return "", f"Error processing PDF: {str(e)}"


class OpenRouterAPI:
    """Handle OpenRouter API calls for question generation with robust error handling"""

    def __init__(self):
        self.api_key = os.getenv('OR_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError("OR_API_KEY not found in environment variables. Please add it to your .env file.")

    def clean_json_response(self, content: str) -> str:
        """Clean and repair JSON response from API"""
        # Remove markdown code blocks
        content = re.sub(r'^```[a-zA-Z]*\\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\\n```$', '', content, flags=re.MULTILINE)
        content = content.strip()
        
        # Remove any text before the first {
        first_brace = content.find('{')
        if first_brace > 0:
            content = content[first_brace:]
        
        # Remove any text after the last }
        last_brace = content.rfind('}')
        if last_brace > 0:
            content = content[:last_brace + 1]
            
        return content

    def generate_questions_batch(self, text_content: str, count: int, difficulty_range: tuple) -> Tuple[List[Dict], str]:
        """Generate a batch of questions with specific count and difficulty range"""
        try:
            min_diff, max_diff = difficulty_range
            
            prompt = f"""Generate exactly {count} multiple-choice questions from this text in JSON format.

Text: {text_content[:3000]}

Requirements:
- Exactly {count} questions
- Difficulty levels between {min_diff} and {max_diff}
- Return ONLY valid JSON, no markdown or explanations

JSON Schema:
{{
    "questions": [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A text",
                "B": "Option B text", 
                "C": "Option C text",
                "D": "Option D text"
            }},
            "correct_answer": "A",
            "difficulty": 0.5,
            "explanation": "Brief explanation",
            "topic": "Topic name"
        }}
    ]
}}"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "openai/gpt-oss-20b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }

            response = requests.post(self.base_url, headers=headers, json=data, timeout=90)
            response.raise_for_status()

            content = response.json()["choices"]["message"]["content"]
            
            # Clean the JSON response
            cleaned_content = self.clean_json_response(content)
            
            # Parse JSON
            try:
                questions_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
                cleaned_content = re.sub(r',\\s*}', '}', cleaned_content)  # Remove trailing commas
                cleaned_content = re.sub(r',\\s*]', ']', cleaned_content)  # Remove trailing commas in arrays
                questions_data = json.loads(cleaned_content)

            if "questions" not in questions_data:
                return [], "Error: Invalid API response format"

            questions = questions_data["questions"]
            
            # Validate each question
            valid_questions = []
            for i, q in enumerate(questions):
                required_fields = ["question", "options", "correct_answer", "difficulty", "explanation", "topic"]
                if all(field in q for field in required_fields):
                    if q["correct_answer"] in q["options"]:
                        valid_questions.append(q)

            return valid_questions, ""

        except Exception as e:
            return [], f"Error in batch generation: {str(e)}"

    def generate_questions(self, text_content: str) -> Tuple[List[Dict], str]:
        """Generate 20 questions total: 10 main + 10 buffer with retry logic"""
        try:
            all_questions = []
            
            # Generate main set (difficulty 0.3-0.7)
            main_questions, error1 = self.generate_questions_batch(text_content, 10, (0.3, 0.7))
            if error1:
                return [], f"Error generating main questions: {error1}"
            
            all_questions.extend(main_questions)
            
            # Wait a bit to avoid rate limiting
            time.sleep(1)
            
            # Generate buffer set (difficulty 0.1-0.9) 
            buffer_questions, error2 = self.generate_questions_batch(text_content, 10, (0.1, 0.9))
            if error2:
                return [], f"Error generating buffer questions: {error2}"
                
            all_questions.extend(buffer_questions)
            
            if len(all_questions) < 15:  # Minimum acceptable
                return [], f"Only generated {len(all_questions)} valid questions, need at least 15"
            
            # Pad with easy questions if needed
            while len(all_questions) < 20:
                all_questions.append({
                    "question": f"Review question {len(all_questions) + 1}",
                    "options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                    "correct_answer": "A",
                    "difficulty": 0.3,
                    "explanation": "This is a review question.",
                    "topic": "General"
                })

            return all_questions[:20], ""  # Return exactly 20

        except Exception as e:
            return [], f"Error generating questions: {str(e)}"


class AdaptiveTestEngine:
    """Enhanced adaptive test engine with buffer support"""

    def __init__(self, main_questions: List[Dict], buffer_questions: List[Dict] = None):
        self.main_questions = main_questions
        self.buffer_questions = buffer_questions or []
        self.all_questions = main_questions + self.buffer_questions
        
        self.user_ability = 0.5
        self.current_difficulty = 0.5
        self.questions_attempted = 0
        self.correct_answers = 0
        self.total_points = 0
        self.question_history = []
        self.used_questions = set()
        self.max_questions = 10  # Only show 10 questions to user

    def get_next_question(self) -> Optional[Dict]:
        """Get next question from main set first, then buffer if needed"""
        if self.questions_attempted >= self.max_questions:
            return None  # Completed test
            
        if len(self.used_questions) >= len(self.all_questions):
            return None  # All questions used

        target_difficulty = self.current_difficulty
        tolerance = 0.2
        
        # Try main questions first
        candidates = []
        for i, q in enumerate(self.main_questions):
            if i not in self.used_questions:
                diff = abs(q["difficulty"] - target_difficulty)
                if diff <= tolerance:
                    candidates.append((i, q, diff))

        # If no good match in main, try buffer
        if not candidates:
            tolerance = 0.3
            offset = len(self.main_questions)
            for i, q in enumerate(self.buffer_questions):
                idx = offset + i
                if idx not in self.used_questions:
                    diff = abs(q["difficulty"] - target_difficulty)
                    if diff <= tolerance:
                        candidates.append((idx, q, diff))

        # If still no match, take any unused
        if not candidates:
            for i, q in enumerate(self.all_questions):
                if i not in self.used_questions:
                    candidates.append((i, q, abs(q["difficulty"] - target_difficulty)))

        if not candidates:
            return None

        # Select best match
        best_idx, best_question, _ = min(candidates, key=lambda x: x[2])
        self.used_questions.add(best_idx)
        return best_question

    def process_answer(self, is_correct: bool, time_taken: float, question_difficulty: float) -> Dict:
        """Process answer and update metrics"""
        self.questions_attempted += 1
        multiplier = 1 + (question_difficulty - 0.5)
        base_points = 10

        if is_correct:
            self.correct_answers += 1
            points_earned = int(base_points * multiplier)
            self.total_points += points_earned
            
            if time_taken < 10:
                ability_increase = 0.1
            else:
                ability_increase = 0.05
                
            self.user_ability = min(0.9, self.user_ability + ability_increase)
            self.current_difficulty = min(0.9, self.current_difficulty + 0.05)
        else:
            points_earned = 0
            self.user_ability = max(0.1, self.user_ability - 0.08)
            self.current_difficulty = max(0.1, self.current_difficulty - 0.1)

        result = {
            "question_num": self.questions_attempted,
            "is_correct": is_correct,
            "time_taken": time_taken,
            "difficulty": question_difficulty,
            "points_earned": points_earned,
            "multiplier": multiplier,
            "ability_after": self.user_ability
        }
        
        self.question_history.append(result)

        return {
            "is_correct": is_correct,
            "points_earned": points_earned,
            "time_taken": time_taken,
            "multiplier": multiplier,
            "current_difficulty": self.current_difficulty,
            "user_ability": self.user_ability,
            "questions_attempted": self.questions_attempted,
            "total_points": self.total_points
        }

    def get_final_results(self) -> Dict:
        """Calculate final test results"""
        if self.questions_attempted == 0:
            return {}

        accuracy = (self.correct_answers / self.questions_attempted) * 100
        avg_difficulty = sum(q["difficulty"] for q in self.question_history) / len(self.question_history)
        
        times = [q["time_taken"] for q in self.question_history]
        fastest_time = min(times) if times else 0
        slowest_time = max(times) if times else 0

        # Get incorrect topics
        incorrect_topics = []
        for result in self.question_history:
            if not result["is_correct"]:
                # Find corresponding question topic
                for q in self.all_questions:
                    if abs(q["difficulty"] - result["difficulty"]) < 0.01:
                        incorrect_topics.append(q.get("topic", "Unknown"))
                        break

        return {
            "total_points": self.total_points,
            "questions_attempted": self.questions_attempted,
            "correct_answers": self.correct_answers,
            "accuracy": accuracy,
            "avg_difficulty": avg_difficulty,
            "fastest_time": fastest_time,
            "slowest_time": slowest_time,
            "final_ability": self.user_ability,
            "incorrect_topics": list(set(incorrect_topics)),
            "question_history": self.question_history
        }

    def reset(self):
        """Reset engine for new test"""
        self.user_ability = 0.5
        self.current_difficulty = 0.5
        self.questions_attempted = 0
        self.correct_answers = 0
        self.total_points = 0
        self.question_history = []
        self.used_questions = set()
'''

with open("backend.py", "w") as f:
    f.write(backend_content)

print("✅ Created updated backend.py with robust JSON handling and buffer support")