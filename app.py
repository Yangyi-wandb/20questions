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
                {"role": "system", "content": """Generate a single common, concrete noun that would work well for a 20 questions game. 
                The object should be:
                - Something physical and tangible
                - Common enough that most people would know it
                - Simple (not a complex or compound object)
                - Family-friendly
                Respond with just the noun in lowercase, nothing else."""},
                {"role": "user", "content": "Generate a random object."}
            ],
            max_tokens=10,
            temperature=1.0
        )
        object_generated = response.choices[0].message.content.strip().lower()
        return object_generated
    except Exception as e:
        fallback_objects = ["book", "chair", "phone", "cup", "pen"]
        return random.choice(fallback_objects)

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
    if 'target_object' not in st.session_state:
        st.session_state.target_object = generate_random_object()
    if 'questions_asked' not in st.session_state:
        st.session_state.questions_asked = []
    if 'question_count' not in st.session_state:
        st.session_state.question_count = 0
    if 'game_over' not in st.session_state:
        st.session_state.game_over = False

def main():
    st.title("20 Questions Game 🎮")
    
    # Initialize game state
    initialize_game_state()
    
    # Display game instructions
    st.markdown("""
    ### How to Play:
    1. Think of a question that can be answered with Yes/No
    2. You have 10 questions to guess the object
    3. Make your guess when you're ready!
    """)

    # Display questions left
    st.write(f"Questions remaining: {10 - st.session_state.question_count}")

    # Question input
    question = st.text_input("Ask a yes/no question:", disabled=st.session_state.game_over)

    # Submit question button
    if st.button("Ask", disabled=st.session_state.game_over):
        if question:
            # Process and log the question
            qa_result = process_question(question, st.session_state.target_object)
            st.session_state.questions_asked.append((qa_result["question"], qa_result["answer"]))
            st.session_state.question_count += 1

    # Make a guess
    guess = st.text_input("Make your guess:", disabled=st.session_state.game_over)
    
    if st.button("Submit Guess", disabled=st.session_state.game_over):
        # Process and log the guess
        guess_result = process_guess(guess, st.session_state.target_object)
        
        if guess_result["is_correct"]:
            st.success(f"🎉 Congratulations! You got it right! It was a {st.session_state.target_object}!")
            st.session_state.game_over = True
        else:
            st.error("Sorry, that's not correct! Try asking more questions.")
            if st.session_state.question_count >= 10:
                st.error(f"Game Over! The object was: {st.session_state.target_object}")
                st.session_state.game_over = True

    # Display question history
    if st.session_state.questions_asked:
        st.write("### Question History:")
        for q, a in st.session_state.questions_asked:
            st.write(f"Q: {q}")
            st.write(f"A: {a}")

    # New game button
    if st.button("New Game") or st.session_state.question_count >= 10:
        # Generate and log new target object
        new_object = generate_random_object()
        st.session_state.target_object = new_object
        st.session_state.questions_asked = []
        st.session_state.question_count = 0
        st.session_state.game_over = False
        st.rerun()

if __name__ == "__main__":
    main()