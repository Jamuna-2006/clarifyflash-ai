import streamlit as st
import os
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# ===================== CONFIG =====================
load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")
if not HF_API_KEY:
    st.error("Hugging Face API key missing")
    st.stop()

client = InferenceClient(token=HF_API_KEY)

st.set_page_config(
    page_title="ClarifyFlash AI",
    page_icon="⚡",
    layout="wide"
)

# ===================== THEME =====================
st.markdown("""
<style>
body { background-color: #1e1b4b; }
h1, h2, h3 { color: #c4b5fd; }
p, li, label { color: #ede9fe; }
.sidebar { background-color: #312e81; }

.stButton > button {
    background-color: #7c3aed;
    color: white;
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 600;
}

.card {
    background-color: #312e81;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    border: 1px solid #4c1d95;
}
</style>
""", unsafe_allow_html=True)

# ===================== HELPERS =====================
def ask_ai(prompt, tokens=400):
    response = client.chat_completion(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=tokens
    )
    return response.choices[0].message.content


def clean(text):
    text = re.sub(r"\b\d+\.\s*", "", text)
    text = re.sub(r"\b(card|flashcard)\s*\d*\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def parse_mcq(text):
    questions = []
    blocks = text.split("\n\n")
    for block in blocks:
        lines = block.splitlines()
        if len(lines) >= 5:
            q = lines[0]
            opts = lines[1:5]
            questions.append((q, opts))
    return questions


def generate_mcq(topic):
    q_text = ask_ai(
        f"""
Create exactly 5 MCQ questions on {topic}.
Strict format:
1. Question
a) option
b) option
c) option
d) option
Do NOT include answers.
"""
    )

    a_text = ask_ai(
        f"""
Give ONLY answers.
Format:
1. a
2. b
3. c
4. d
5. a

Questions:
{q_text}
""",
        tokens=200
    )

    return q_text, a_text


def generate_true_false(topic):
    q_text = ask_ai(
        f"""
Create exactly 5 True/False questions on {topic}.
Each question on a new line.
Do NOT include answers.
"""
    )

    a_text = ask_ai(
        f"""
Give ONLY answers (True or False).
Format:
1. True
2. False
3. True
4. False
5. True

Questions:
{q_text}
""",
        tokens=150
    )

    return q_text, a_text


# ===================== SIDEBAR =====================
st.sidebar.title("⚡ ClarifyFlash AI")
page = st.sidebar.radio(
    "Select feature:",
    ["📘 Summary", "🧠 Flash Cards", "📝 Quiz", "✅ True / False"]
)
topic = st.sidebar.text_input("Enter Topic (English)")

st.title("ClarifyFlash AI – Professional Study Buddy")

# ===================== SUMMARY =====================
if page == "📘 Summary":
    if st.button("Generate Summary"):
        if not topic:
            st.warning("Enter a topic")
        else:
            summary = ask_ai(
                f"Explain {topic} in simple English using clear bullet points."
            )
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.write(summary)
            st.markdown("</div>", unsafe_allow_html=True)

# ===================== FLASH CARDS =====================
elif page == "🧠 Flash Cards":
    if st.button("Generate Flash Cards"):
        if not topic:
            st.warning("Enter a topic")
        else:
            cards = ask_ai(
                f"""
Create exactly 5 flash cards for {topic}.
Format:
Q: question
A: short answer
Do NOT include card numbers.
"""
            )

            for block in cards.split("Q:"):
                if "A:" in block:
                    q, a = block.split("A:", 1)
                    with st.expander(f"🃏 {clean(q)}"):
                        st.markdown("<div class='card'>", unsafe_allow_html=True)
                        st.write(clean(a))
                        st.markdown("</div>", unsafe_allow_html=True)

# ===================== MCQ QUIZ =====================
elif page == "📝 Quiz":
    if st.button("Generate Quiz"):
        if not topic:
            st.warning("Enter a topic")
        else:
            q_text, a_text = generate_mcq(topic)
            st.session_state.mcq_q = q_text
            st.session_state.mcq_a = a_text

    if "mcq_q" in st.session_state:
        st.subheader("📝 MCQ Quiz")

        questions = parse_mcq(st.session_state.mcq_q)
        user_answers = []
        correct = re.findall(r"[a-d]", st.session_state.mcq_a.lower())

        for i, (q, opts) in enumerate(questions):
            st.write(q)
            choice = st.radio(
                "Choose an option:",
                opts,
                key=f"mcq_{i}"
            )
            user_answers.append(choice[0].lower())

        if st.button("Submit Quiz"):
            score = sum(
                1 for i in range(len(correct))
                if user_answers[i] == correct[i]
            )
            st.success(f"🎯 Your Score: {score} / {len(correct)}")

        combined = f"{st.session_state.mcq_q}\n\nAnswers:\n{st.session_state.mcq_a}"
        st.download_button(
            "⬇️ Download MCQ (Questions + Answers)",
            combined,
            file_name="mcq_quiz.txt"
        )

# ===================== TRUE / FALSE =====================
elif page == "✅ True / False":
    if st.button("Generate True / False"):
        if not topic:
            st.warning("Enter a topic")
        else:
            q_text, a_text = generate_true_false(topic)
            st.session_state.tf_q = q_text
            st.session_state.tf_a = a_text

    if "tf_q" in st.session_state:
        st.subheader("✅ True / False Quiz")

        questions = st.session_state.tf_q.splitlines()
        answers = re.findall(r"true|false", st.session_state.tf_a.lower())
        user_ans = []

        for i, q in enumerate(questions):
            if q.strip():
                st.write(q)
                choice = st.radio(
                    "Select:",
                    ["True", "False"],
                    key=f"tf_{i}"
                )
                user_ans.append(choice.lower())

        if st.button("Submit True / False"):
            score = sum(
                1 for i in range(len(answers))
                if user_ans[i] == answers[i]
            )
            st.success(f"🎯 Your Score: {score} / {len(answers)}")

        combined = f"{st.session_state.tf_q}\n\nAnswers:\n{st.session_state.tf_a}"
        st.download_button(
            "⬇️ Download True/False (Questions + Answers)",
            combined,
            file_name="true_false.txt"
        )
