import os
import json
import openai
import weave
import streamlit as st
from typing import Dict, List, Optional
from dataclasses import dataclass

# Determine if we're running in a Streamlit Cloud environment
is_streamlit_cloud = os.environ.get('STREAMLIT_RUNTIME') == 'true'
if is_streamlit_cloud:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = os.getenv("OPENAI_API_KEY")

@dataclass
class GameResponse:
    object_name: str
    hints: List[str]
    qa_response: Optional[str] = None

class TwentyQuestionsModel(weave.Model):
    def __init__(self):
        super().__init__()
        self.model_name = 'gpt-3.5-turbo'
        self.client = openai.AsyncClient(api_key=api_key)
        
        self.object_prompt_template = """Generate a random object for a 20 questions game. 
        The object MUST be:
        - Something extremely common that everyone encounters regularly
        - A single word if possible (two words max)
        - Something found in most homes or offices
        - Simple and basic (no specialized equipment)
        - Something a child would recognize
        
        Examples of good objects:
        - pencil
        - book
        - spoon
        - clock
        - chair
        
        AVOID:
        - Specialized items (garden gnome, violin, etc.)
        - Complex items (laptop, smartphone, etc.)
        - Brand-specific items
        - Regional or cultural-specific items
        - Uncommon or luxury items
        
        Respond with a JSON object containing a single field "object": <str>"""

        self.hint_prompt_template = """Generate a cryptic, clever hint for the object '{object}'.
        The hint MUST:
        - Be abstract or metaphorical
        - Never mention the object's direct use or common location
        - Use wordplay, analogies, or indirect references
        - Be challenging but not impossible to decode
        
        Previous hints: {previous_hints}
        
        Respond with a JSON object containing a single field "hint": <str>"""

        self.qa_prompt_template = """You are playing a 20 questions game. The object is '{object}'.
        Question: {question}
        
        Respond with a JSON object containing a single field "answer": <str> that must be either "Yes", "No", or "Maybe"."""

    @weave.op()
    async def predict_object(self) -> Dict:
        """Generate a random object for the game."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.object_prompt_template}
                ],
            )
            result = response.choices[0].message.content
            if result is None:
                raise ValueError("No response from model")
            return json.loads(result)
        except Exception as e:
            # Fallback to basic objects if API fails
            fallback_objects = ["pencil", "book", "spoon", "clock", "chair"]
            return {"object": random.choice(fallback_objects)}

    @weave.op()
    async def predict_hint(self, object_name: str, previous_hints: List[str]) -> Dict:
        """Generate a hint for the given object."""
        try:
            previous_hints_str = "; ".join(previous_hints) if previous_hints else "none"
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.hint_prompt_template.format(
                        object=object_name,
                        previous_hints=previous_hints_str
                    )}
                ],
            )
            result = response.choices[0].message.content
            if result is None:
                raise ValueError("No response from model")
            return json.loads(result)
        except Exception as e:
            return {"hint": f"This object might be found in everyday life."}

    @weave.op()
    async def predict_answer(self, object_name: str, question: str) -> Dict:
        """Generate an answer for the given question about the object."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.qa_prompt_template.format(
                        object=object_name,
                        question=question
                    )}
                ],
            )
            result = response.choices[0].message.content
            if result is None:
                raise ValueError("No response from model")
            return json.loads(result)
        except Exception as e:
            return {"answer": "Maybe"}

    @weave.op()
    async def predict(self, input_data: Dict) -> GameResponse:
        """Main predict function that handles different types of predictions."""
        if input_data.get("type") == "new_game":
            # Generate a new object
            object_result = await self.predict_object()
            return GameResponse(
                object_name=object_result["object"],
                hints=[]
            )
        
        elif input_data.get("type") == "hint":
            # Generate a hint for existing object
            hint_result = await self.predict_hint(
                input_data["object"],
                input_data.get("previous_hints", [])
            )
            return GameResponse(
                object_name=input_data["object"],
                hints=[hint_result["hint"]]
            )
        
        elif input_data.get("type") == "question":
            # Answer a question about the object
            answer_result = await self.predict_answer(
                input_data["object"],
                input_data["question"]
            )
            return GameResponse(
                object_name=input_data["object"],
                hints=[],
                qa_response=answer_result["answer"]
            )
        
        else:
            raise ValueError("Invalid prediction type")

# Example usage:
async def main():
    # Initialize Weave with the project name
    weave.init("wandb-designers/20questions")
    
    # Initialize model
    model = TwentyQuestionsModel()
    
    # Start new game
    game_response = await model.predict({"type": "new_game"})
    print(f"Generated object: {game_response.object_name}")
    
    # Get a hint
    hint_response = await model.predict({
        "type": "hint",
        "object": game_response.object_name,
        "previous_hints": []
    })
    print(f"Hint: {hint_response.hints[0]}")
    
    # Ask a question
    qa_response = await model.predict({
        "type": "question",
        "object": game_response.object_name,
        "question": "Is it electronic?"
    })
    print(f"Answer: {qa_response.qa_response}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())