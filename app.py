import streamlit as st
from groq import Groq
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import random
from gtts import gTTS
import tempfile
import os
import base64

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="MediAssist AI",
    page_icon="🩺",
    layout="wide"
)

# ---------------- GROQ CLIENT ----------------

# ✅ FIXED: use environment variable properly
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")  # Paste your own API key
)

# ---------------- TTS ----------------

def text_to_speech_autoplay(text):
    tts = gTTS(text=text, lang='en')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp_file.name)

    with open(temp_file.name, "rb") as f:
        audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()

    return audio_base64

# ---------------- BMI FUNCTIONS ----------------

def calculate_bmi(weight_kg, height_m):
    return round(weight_kg / (height_m ** 2), 2)

def interpret_bmi(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def convert_units(weight, weight_unit, height, height_unit):
    weight_kg = weight * 0.453592 if weight_unit == "lb" else weight

    if height_unit == "cm":
        height_m = height / 100
    elif height_unit == "inches":
        height_m = height * 0.0254
    else:
        raise ValueError("Invalid height unit")

    return weight_kg, height_m

# ---------------- PDF GENERATOR ----------------

def create_pdf(report_text):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MediAssist AI Medical Report", styles['Title']))
    story.append(Spacer(1, 20))

    for line in report_text.split("\n"):
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 5))

    doc = SimpleDocTemplate(buffer)
    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------- MEDICAL CHATBOT ----------------

class MediAssistBot:
    def __init__(self):
        self.context = {}
        self.extra_questions = 0
        self.questions = {
            "symptoms": ["Please describe your main symptoms."],
            "duration": ["How long have you been experiencing these symptoms?"],
            "severity": ["On a scale from 1 to 10, how severe are the symptoms?"],
            "extra": [
                "Do you have fever, chills, or body pain?",
                "Are you experiencing cough or breathing difficulty?",
                "Do you feel nausea, vomiting, or stomach pain?",
                "Have you taken any medicine already?"
            ]
        }

    def update_context(self, key, value):
        if key == "extra":
            self.context.setdefault("extra", []).append(value)
        else:
            self.context[key] = value

    def get_next_question(self):
        if "symptoms" not in self.context:
            return random.choice(self.questions["symptoms"])
        if "duration" not in self.context:
            return random.choice(self.questions["duration"])
        if "severity" not in self.context:
            return random.choice(self.questions["severity"])
        if self.extra_questions < 2:
            self.extra_questions += 1
            return random.choice(self.questions["extra"])
        return None

    def generate_report(self):
        # ✅ SAFE ACCESS (no KeyError)
        prompt = f"""
You are a professional medical AI assistant.

Patient Information:
Name: {self.context.get('name', 'Unknown')}
Age: {self.context.get('age', 'Unknown')}
BMI: {self.context.get('bmi', 'Unknown')} ({self.context.get('bmi_category', '')})

Symptoms: {self.context.get('symptoms', '')}
Duration: {self.context.get('duration', '')}
Severity: {self.context.get('severity', '')}
Additional Info: {self.context.get('extra')}

Provide analysis in this structure:

Possible Conditions
• condition

Most Likely Condition
• condition

Suggested Medicines
• Generic – purpose
  Brands: brand1, brand2

Home Care Advice
• advice

Doctor Warning Signs
• warning
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content

# ---------------- SESSION STATE ----------------

if "bot" not in st.session_state:
    st.session_state.bot = MediAssistBot()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "question" not in st.session_state:
    st.session_state.question = None
if "pdf" not in st.session_state:
    st.session_state.pdf = None
if "audio" not in st.session_state:
    st.session_state.audio = None

bot = st.session_state.bot

# ---------------- HEADER ----------------

st.title("🩺 MediAssist AI Healthcare Assistant")

st.markdown("""
MediAssist is an **AI-powered symptom checker**.

⚠️ This system does not replace professional medical advice.
""")

# ---------------- PATIENT FORM ----------------

st.subheader("Step 1: Patient Information")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    name = st.text_input("Name")
with col2:
    age = st.number_input("Age", 1, 120)
with col3:
    height_unit = st.selectbox("Height Unit", ["cm", "inches"])
with col4:
    height_value = st.number_input("Height", min_value=20.0, max_value=300.0)
with col5:
    weight_unit = st.selectbox("Weight Unit", ["kg", "lb"])
with col6:
    weight_value = st.number_input("Weight", min_value=10.0, max_value=700.0)

bmi = None
bmi_category = None

if height_value and weight_value:
    weight_kg, height_m = convert_units(weight_value, weight_unit, height_value, height_unit)
    bmi = calculate_bmi(weight_kg, height_m)
    bmi_category = interpret_bmi(bmi)
    st.success(f"Calculated BMI: **{bmi}** ({bmi_category})")

# ✅ store context safely
if name and age and bmi:
    bot.context.update({
        "name": name,
        "age": age,
        "bmi": bmi,
        "bmi_category": bmi_category
    })

# ---------------- RESET ----------------

if st.button("Start New Checkup"):
    st.session_state.bot = MediAssistBot()
    st.session_state.messages = []
    st.session_state.question = None
    st.session_state.pdf = None
    st.session_state.audio = None
    st.rerun()


# ---------------- NEARBY MEDICAL SERVICES ----------------

st.subheader("🌍 Nearby Medical Services")

st.markdown("""
Find hospitals, clinics, and pharmacies within **1 km of your location**.

👉 Click below and allow location access in your browser.
""")

flask_app_url = "http://127.0.0.1:5000/"

# ✅ Better Streamlit button instead of raw HTML
if st.button("📍 Open Nearby Medical Facilities Map"):
    st.markdown(f"[Click here if not redirected]({flask_app_url})")
    st.components.v1.html(
        f"""
        <script>
            window.open("{flask_app_url}", "_blank");
        </script>
        """,
        height=0,
    )

# ---------------- CHAT ----------------

st.subheader("Step 2: Symptom Discussion")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if name and age and bmi:
    if st.session_state.question is None:
        q = bot.get_next_question()
        if q:
            st.session_state.question = q
            st.session_state.messages.append({"role": "assistant", "content": q})
            st.rerun()


# ---------------- USER INPUT ----------------

user_input = st.chat_input("Type your answer...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    if "symptoms" not in bot.context:
        bot.update_context("symptoms", user_input)
    elif "duration" not in bot.context:
        bot.update_context("duration", user_input)
    elif "severity" not in bot.context:
        bot.update_context("severity", user_input)
    else:
        bot.update_context("extra", user_input)

    next_q = bot.get_next_question()

    if next_q:
        st.session_state.messages.append({"role": "assistant", "content": next_q})
    else:
        # ✅ VALIDATION BEFORE REPORT
        required = ["name", "age", "bmi", "symptoms", "duration", "severity"]
        missing = [k for k in required if k not in bot.context]

        if missing:
            st.error(f"Missing data: {missing}")
            st.stop()

        with st.spinner("Analyzing symptoms..."):
            report = bot.generate_report()

        audio_base64 = text_to_speech_autoplay(report)
        st.session_state.audio = audio_base64

        pdf_file = create_pdf(report)
        st.session_state.pdf = pdf_file

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"### 🩺 Health Analysis\n\n{report}"
        })

    st.rerun()

# ---------------- AUDIO ----------------

if st.session_state.audio:
    st.markdown(f"""
    <audio autoplay>
        <source src="data:audio/mp3;base64,{st.session_state.audio}" type="audio/mp3">
    </audio>
    """, unsafe_allow_html=True)


# ---------------- PDF ----------------

if st.session_state.pdf:
    st.subheader("Step 3: Download Medical Report")
    st.download_button(
        "📄 Download Health Report (PDF)",
        data=st.session_state.pdf,
        file_name="mediassist_health_report.pdf",
        mime="application/pdf"
    )
