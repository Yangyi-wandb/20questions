import streamlit as st
import openai
import random

# List of simple objects for the game
OBJECTS = [
    "cat", "dog", "book", "phone", "chair", "table", "car", "tree", 
    "house", "bicycle", "computer", "pencil", "shoe", "cup", "clock"
]

def initialize_game_state():
    if 'target_object' not in st.session_state:
        st.session_state.target_object = random.choice(OBJECTS)
    if 'questions_asked' not in st.session_state:
        st.session_state.questions_asked = []
    if 'question_count' not in st.session_state:
        st.session_state.question_count = 0
    if 'game_over' not in st.session_state:
        st.session_state.game_over = False

def get_ai_response(question, target_object):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are playing a 20 questions game. The object is '{target_object}'. Answer only with 'Yes', 'No', or 'Maybe'. Be accurate but don't reveal what the object is."},
                {"role": "user", "content": question}
            ],
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Error connecting to OpenAI. Please try again."

def main():
    st.title("20 Questions Game 🎮")
    
    # Initialize game state
    initialize_game_state()
    
    # Setup OpenAI API key
    openai.api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")
    
    if not openai.api_key:
        st.warning("Please enter your OpenAI API key to play.")
        return

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
            answer = get_ai_response(question, st.session_state.target_object)
            st.session_state.questions_asked.append((question, answer))
            st.session_state.question_count += 1

    # Make a guess
    guess = st.text_input("Make your guess:", disabled=st.session_state.game_over)
    
    if st.button("Submit Guess", disabled=st.session_state.game_over):
        if guess.lower() == st.session_state.target_object.lower():
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
        st.session_state.target_object = random.choice(OBJECTS)
        st.session_state.questions_asked = []
        st.session_state.question_count = 0
        st.session_state.game_over = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()