import os
import weave
import streamlit as st
from openai import OpenAI
import random

# Determine if we're running in a Streamlit Cloud environment
is_streamlit_cloud = os.environ.get('STREAMLIT_RUNTIME') == 'true'
if is_streamlit_cloud:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

weave.init("wandb-designers/20questions")

@weave.op()
def generate_random_object():
    """Generate and log a random object for the game."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Generate a random object for a 20 questions game. Pick from a wide variety of categories:
                
                Categories to consider:
                - Kitchen items
                - Tools and equipment
                - Electronics and gadgets
                - Sports equipment
                - Musical instruments
                - Transportation items
                - Clothing and accessories
                - Outdoor/garden items
                - Art supplies
                - Toys and games
                
                The object should be:
                - A single, physical, tangible item
                - Common enough to be widely known
                - Not a brand name
                - Specific (e.g., 'tennis racket' instead of just 'racket')
                - Family-friendly
                
                Respond with just the object name in lowercase, nothing else."""},
                {"role": "user", "content": "Generate a specific, random object from any category."}
            ],
            max_tokens=10,
            temperature=1.0  # Maximum randomness
        )
        object_generated = response.choices[0].message.content.strip().lower()
        return object_generated
    except Exception as e:
        # Expanded fallback list with more variety
        fallback_objects = [
            "tennis ball", "coffee mug", "hammer", "umbrella", "violin",
            "backpack", "watering can", "paintbrush", "flashlight", "compass",
            "guitar pick", "measuring tape", "cooking pot", "bicycle pump", "dice"
        ]
        return random.choice(fallback_objects)

@weave.op()
def generate_hint(target_object: str, previous_hints: list):
    """Generate and log a hint for the target object."""
    try:
        previous_hints_str = "\nPrevious hints: " + "; ".join(previous_hints) if previous_hints else ""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""Generate a cryptic, clever hint for the object '{target_object}'.
                The hint MUST:
                - Be abstract or metaphorical
                - Never mention the object's direct use or common location
                - Use wordplay, analogies, or indirect references
                - Be different from these previous hints: {previous_hints_str}
                - Be challenging but not impossible to decode
                
                Examples for a "book":
                BAD (too obvious): "You can read this object"
                GOOD: "Time's whispers caught in paper dreams"
                
                For a "chair":
                BAD (too obvious): "You sit on this furniture"
                GOOD: "Four-legged throne for common kings"
                
                For a "phone":
                BAD (too obvious): "You use this to call people"
                GOOD: "Pocket portal to distant worlds"
                
                Respond with just the hint, nothing else."""},
                {"role": "user", "content": "Generate a cryptic hint."}
            ],
            max_tokens=50,
            temperature=0.9
        )
        hint = response.choices[0].message.content.strip()
        return {
            "target_object": target_object,
            "hint": hint,
            "hint_number": len(previous_hints) + 1
        }
    except Exception as e:
        return {
            "target_object": target_object,
            "hint": "Unable to generate hint. Please try again.",
            "hint_number": len(previous_hints) + 1
        }

@weave.op()
def process_question(question: str, target_object: str):
    """Process and log a user's question and the AI's response."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are playing a 20 questions game. The object is '{target_object}'. Answer only with 'Yes', 'No', or 'Maybe'. Be accurate but don't reveal what the object is."},
                {"role": "user", "content": question}
            ],
            max_tokens=50
        )
        ai_answer = response.choices[0].message.content.strip()
        return {
            "question": question,
            "answer": ai_answer,
            "target_object": target_object
        }
    except Exception as e:
        return {
            "question": question,
            "answer": "Error connecting to OpenAI. Please try again.",
            "target_object": target_object
        }

@weave.op()
def process_guess(guess: str, target_object: str):
    """Process and log a user's guess and the result."""
    is_correct = guess.lower() == target_object.lower()
    return {
        "guess": guess,
        "target_object": target_object,
        "is_correct": is_correct
    }

def initialize_game_state():
    """Initialize or reset game state."""
    # Only generate a new object if one doesn't exist
    if 'target_object' not in st.session_state:
        st.session_state.target_object = generate_random_object()
    
    if 'questions_asked' not in st.session_state:
        st.session_state.questions_asked = []
    if 'question_count' not in st.session_state:
        st.session_state.question_count = 0
    if 'game_over' not in st.session_state:
        st.session_state.game_over = False
    if 'hints_used' not in st.session_state:
        st.session_state.hints_used = []
    if 'hints_remaining' not in st.session_state:
        st.session_state.hints_remaining = 2

def reset_game():
    """Reset the game with a new object."""
    new_object = generate_random_object()
    # Update all game state at once to avoid async issues
    st.session_state.update({
        'target_object': new_object,
        'questions_asked': [],
        'question_count': 0,
        'game_over': False,
        'hints_used': [],
        'hints_remaining': 2
    })

def main():
    # Make sure these configurations are set before any Streamlit elements
    st.set_page_config(
        page_title="20 Questions Game",
        initial_sidebar_state="collapsed"
    )
    
    st.title("20 Questions Game 🎮")
    
    # Initialize game state
    initialize_game_state()
    
    # Display game instructions
    st.markdown("""
    ### How to Play:
    1. Think of a question that can be answered with Yes/No
    2. You have 20 questions to guess the object
    3. You can use up to 2 hints during the game (they're cryptic!)
    4. Make your guess when you're ready!
    """)

    # Display questions and hints remaining
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Questions remaining: {20 - st.session_state.question_count}")
    with col2:
        st.write(f"Hints remaining: {st.session_state.hints_remaining}")

    # Hint button
    if st.button("Get Hint", disabled=st.session_state.game_over or st.session_state.hints_remaining <= 0, key='hint_button'):
        if st.session_state.hints_remaining > 0:
            hint_result = generate_hint(st.session_state.target_object, st.session_state.hints_used)
            st.session_state.hints_used.append(hint_result["hint"])
            st.session_state.hints_remaining -= 1
            st.info(f"💡 Hint: {hint_result['hint']}")

    # Display previous hints
    if st.session_state.hints_used:
        st.write("### Hints Used:")
        for i, hint in enumerate(st.session_state.hints_used, 1):
            st.write(f"{i}. {hint}")

    # Question input
    question = st.text_input("Ask a yes/no question:", disabled=st.session_state.game_over, key='question_input')

    # Submit question button
    if st.button("Ask", disabled=st.session_state.game_over, key='ask_button'):
        if question:
            qa_result = process_question(question, st.session_state.target_object)
            st.session_state.questions_asked.append((qa_result["question"], qa_result["answer"]))
            st.session_state.question_count += 1

    # Make a guess
    guess = st.text_input("Make your guess:", disabled=st.session_state.game_over, key='guess_input')
    
    if st.button("Submit Guess", disabled=st.session_state.game_over, key='guess_button'):
        guess_result = process_guess(guess, st.session_state.target_object)
        
        if guess_result["is_correct"]:
            st.success(f"🎉 Congratulations! You got it right! It was a {st.session_state.target_object}!")
            st.session_state.game_over = True
        else:
            st.error("Sorry, that's not correct! Try asking more questions.")
            if st.session_state.question_count >= 20:
                st.error(f"Game Over! The object was: {st.session_state.target_object}")
                st.session_state.game_over = True

    # Display question history
    if st.session_state.questions_asked:
        st.write("### Question History:")
        for q, a in st.session_state.questions_asked:
            st.write(f"Q: {q}")
            st.write(f"A: {a}")

    # New game button
    if st.button("New Game", key='new_game_button') or st.session_state.question_count >= 20:
        reset_game()
        st.rerun()

if __name__ == "__main__":
    main()