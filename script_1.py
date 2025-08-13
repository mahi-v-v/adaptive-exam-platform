# Create the updated app.py with all fixes
app_content = '''import streamlit as st
import time
from datetime import datetime
from backend import PDFProcessor, OpenRouterAPI, AdaptiveTestEngine

# Configure Streamlit page
st.set_page_config(
    page_title="AI-Driven Adaptive Testing Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.metrics-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
}
.question-container {
    background-color: #ffffff;
    padding: 2rem;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
    margin: 1rem 0;
}
.result-container {
    background-color: #e8f5e8;
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 5px solid #4caf50;
    margin: 1rem 0;
}
.error-container {
    background-color: #ffeaea;
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 5px solid #f44336;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize all session state variables"""
    if 'page' not in st.session_state:
        st.session_state.page = 'upload'
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = None
    if 'main_questions' not in st.session_state:
        st.session_state.main_questions = None
    if 'buffer_questions' not in st.session_state:
        st.session_state.buffer_questions = None
    if 'test_engine' not in st.session_state:
        st.session_state.test_engine = None
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    if 'question_start_time' not in st.session_state:
        st.session_state.question_start_time = None
    if 'test_completed' not in st.session_state:
        st.session_state.test_completed = False
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None

def render_upload_page():
    """Render the PDF upload page"""
    st.markdown('<h1 class="main-header">🧠 AI-Driven Adaptive Testing Platform</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h3>Upload your study material to generate adaptive questions</h3>
        <p>This platform creates 20 questions but shows only 10 in your test, with smart difficulty adaptation.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="question-container">', unsafe_allow_html=True)
        st.subheader("📄 Upload PDF Study Material")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a PDF containing your study material. The system will extract text and generate questions."
        )
        
        if uploaded_file is not None:
            st.info(f"📁 Uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")
            
            if st.button("🚀 Process PDF & Generate Questions", type="primary"):
                with st.spinner("Processing PDF and generating adaptive questions..."):
                    # Extract text from PDF
                    processor = PDFProcessor()
                    extracted_text, error = processor.extract_text_from_pdf(uploaded_file)
                    
                    if error:
                        st.markdown(f'<div class="error-container"><strong>❌ {error}</strong></div>', 
                                  unsafe_allow_html=True)
                        return
                    
                    st.session_state.pdf_text = extracted_text
                    st.success(f"✅ Successfully extracted {len(extracted_text)} characters from PDF")
                    
                    # Generate questions using OpenRouter API
                    try:
                        api_client = OpenRouterAPI()
                        all_questions, api_error = api_client.generate_questions(extracted_text)
                        
                        if api_error:
                            st.markdown(f'<div class="error-container"><strong>❌ {api_error}</strong></div>', 
                                      unsafe_allow_html=True)
                            return
                        
                        # Split into main (first 10) and buffer (last 10)
                        st.session_state.main_questions = all_questions[:10]
                        st.session_state.buffer_questions = all_questions[10:]
                        
                        st.success(f"✅ Generated {len(st.session_state.main_questions)} main questions + {len(st.session_state.buffer_questions)} buffer questions")
                        
                        # Initialize test engine with both sets
                        st.session_state.test_engine = AdaptiveTestEngine(
                            st.session_state.main_questions,
                            st.session_state.buffer_questions
                        )
                        
                        st.session_state.page = 'test'
                        st.rerun()
                        
                    except Exception as e:
                        st.markdown(f'<div class="error-container"><strong>❌ Error: {str(e)}</strong></div>', 
                                  unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Instructions
    st.markdown("---")
    st.markdown("""
    ### 📋 How it works:
    1. **Upload**: Select a PDF file with your study material
    2. **Process**: The system extracts text and generates 20 adaptive questions
    3. **Test**: Answer 10 questions that adapt to your knowledge level (10 more as smart backup)
    4. **Learn**: Get detailed results and improvement suggestions
    
    ### ⚙️ Features:
    - **Adaptive Difficulty**: Questions get harder or easier based on your performance
    - **Smart Question Pool**: 20 generated, 10 shown, with intelligent buffer usage
    - **Real-time Metrics**: Track your progress, difficulty level, and ability score
    - **Smart Scoring**: Harder questions give more points
    - **Detailed Results**: Get insights on your strengths and areas for improvement
    """)

def render_test_page():
    """Render the adaptive test interface"""
    if not st.session_state.test_engine:
        st.error("No test engine available. Please upload a PDF first.")
        if st.button("← Back to Upload"):
            st.session_state.page = 'upload'
            st.rerun()
        return
    
    engine = st.session_state.test_engine
    
    # Check if test is completed
    if engine.questions_attempted >= engine.max_questions:
        st.session_state.test_completed = True
        st.session_state.page = 'results'
        st.rerun()
        return
    
    # Header with progress
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown('<h1 class="main-header">🧠 Adaptive Test in Progress</h1>', unsafe_allow_html=True)
    with col2:
        st.metric("Questions Done", f"{engine.questions_attempted}/{engine.max_questions}")
    with col3:
        st.metric("Current Score", engine.total_points)
    
    # Get next question if needed
    if st.session_state.current_question is None:
        next_q = engine.get_next_question()
        if next_q is None:
            st.session_state.test_completed = True
            st.session_state.page = 'results'
            st.rerun()
            return
        
        st.session_state.current_question = next_q
        st.session_state.question_start_time = time.time()
        st.session_state.show_feedback = False
    
    # Live metrics display
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Difficulty", f"{engine.current_difficulty:.2f}")
    with col2:
        st.metric("Your Ability", f"{engine.user_ability:.2f}")
    with col3:
        accuracy = (engine.correct_answers/max(1, engine.questions_attempted)*100) if engine.questions_attempted > 0 else 0
        st.metric("Accuracy", f"{accuracy:.1f}%")
    with col4:
        multiplier = 1 + (st.session_state.current_question["difficulty"] - 0.5)
        st.metric("Point Multiplier", f"{multiplier:.2f}x")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Current question
    current_q = st.session_state.current_question
    st.markdown('<div class="question-container">', unsafe_allow_html=True)
    
    st.subheader(f"Question {engine.questions_attempted + 1}")
    st.markdown(f"**Difficulty Level:** {current_q['difficulty']:.2f}")
    st.markdown(f"**Topic:** {current_q['topic']}")
    
    st.markdown("---")
    st.markdown(f"### {current_q['question']}")
    
    # Show feedback if available
    if st.session_state.show_feedback and st.session_state.last_result:
        result = st.session_state.last_result
        time_taken = time.time() - st.session_state.question_start_time
        
        if result['is_correct']:
            st.markdown(f"""<div class="result-container">
                <h4>✅ Correct!</h4>
                <p><strong>Points Earned:</strong> {result['points_earned']}</p>
                <p><strong>Time Taken:</strong> {result['time_taken']:.1f} seconds</p>
                <p><strong>Explanation:</strong> {current_q['explanation']}</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="error-container">
                <h4>❌ Incorrect</h4>
                <p><strong>Correct Answer:</strong> {current_q['correct_answer']}) {current_q['options'][current_q['correct_answer']]}</p>
                <p><strong>Time Taken:</strong> {result['time_taken']:.1f} seconds</p>
                <p><strong>Explanation:</strong> {current_q['explanation']}</p>
            </div>""", unsafe_allow_html=True)
        
        # Show updated metrics
        st.markdown("### 📊 Updated Metrics:")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("New Difficulty", f"{result['current_difficulty']:.2f}")
        with col2:
            st.metric("New Ability", f"{result['user_ability']:.2f}")
        with col3:
            st.metric("Total Points", result['total_points'])
        with col4:
            st.metric("Questions Left", f"{engine.max_questions - result['questions_attempted']}")
        
        if st.button("Continue to Next Question →", type="primary"):
            st.session_state.current_question = None
            st.session_state.show_feedback = False
            st.session_state.last_result = None
            st.rerun()
    
    else:
        # Answer options
        selected_answer = st.radio(
            "Select your answer:",
            options=list(current_q['options'].keys()),
            format_func=lambda x: f"{x}) {current_q['options'][x]}",
            key=f"q_{engine.questions_attempted}"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submit_clicked = st.button("Submit Answer", type="primary")
        
        # Process answer submission
        if submit_clicked and selected_answer:
            time_taken = time.time() - st.session_state.question_start_time
            is_correct = selected_answer == current_q['correct_answer']
            
            # Process the answer
            result = engine.process_answer(is_correct, time_taken, current_q['difficulty'])
            
            st.session_state.show_feedback = True
            st.session_state.last_result = result
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_results_page():
    """Render the final results page"""
    if not st.session_state.test_engine:
        st.error("No test data available.")
        if st.button("← Back to Upload"):
            st.session_state.page = 'upload'
            st.rerun()
        return
    
    results = st.session_state.test_engine.get_final_results()
    
    st.markdown('<h1 class="main-header">🎉 Test Complete!</h1>', unsafe_allow_html=True)
    
    # Overall Results
    st.markdown('<div class="result-container">', unsafe_allow_html=True)
    st.subheader("📊 Overall Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Points", results['total_points'])
    with col2:
        st.metric("Accuracy", f"{results['accuracy']:.1f}%")
    with col3:
        st.metric("Questions Answered", f"{results['questions_attempted']}/10")
    with col4:
        st.metric("Final Ability Level", f"{results['final_ability']:.2f}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed Metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
        st.subheader("⏱️ Time Analysis")
        st.metric("Fastest Response", f"{results['fastest_time']:.1f}s")
        st.metric("Slowest Response", f"{results['slowest_time']:.1f}s")
        st.metric("Average Difficulty", f"{results['avg_difficulty']:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
        st.subheader("🎯 Areas for Improvement")
        if results['incorrect_topics']:
            for topic in results['incorrect_topics']:
                st.write(f"• {topic}")
        else:
            st.write("🌟 Great job! No specific areas need improvement.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Performance Chart
    if results['question_history']:
        st.subheader("📈 Your Learning Journey")
        
        # Create data for chart
        question_nums = [i+1 for i in range(len(results['question_history']))]
        difficulties = [q['difficulty'] for q in results['question_history']]
        abilities = [q['ability_after'] for q in results['question_history']]
        
        # Simple line chart using Streamlit
        chart_data = {
            'Question': question_nums,
            'Difficulty Faced': difficulties,
            'Your Ability': abilities
        }
        st.line_chart(chart_data, x='Question')
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🔄 Restart Test", type="primary"):
            st.session_state.test_engine.reset()
            st.session_state.current_question = None
            st.session_state.test_completed = False
            st.session_state.show_feedback = False
            st.session_state.last_result = None
            st.session_state.page = 'test'
            st.rerun()
    
    with col2:
        if st.button("📄 Upload New PDF"):
            # Reset everything
            for key in list(st.session_state.keys()):
                if key.startswith(('pdf_', 'main_', 'buffer_', 'test_', 'current_', 'question_', 'show_', 'last_')):
                    del st.session_state[key]
            st.session_state.page = 'upload'
            st.session_state.test_completed = False
            st.rerun()

def main():
    """Main application logic"""
    initialize_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🧠 Navigation")
        
        if st.session_state.page == 'upload':
            st.info("📤 Currently: Upload PDF")
        elif st.session_state.page == 'test':
            st.info("📝 Currently: Taking Test")
        elif st.session_state.page == 'results':
            st.info("📊 Currently: View Results")
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        st.markdown("**API Status:**")
        
        try:
            api_client = OpenRouterAPI()
            st.success("✅ OpenRouter API Connected")
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            st.markdown("""
            **To fix this:**
            1. Create a `.env` file in your project folder
            2. Add your OpenRouter API key: `OR_API_KEY=your_key_here`
            3. Restart the application
            """)
        
        st.markdown("---")
        st.markdown("### 📚 About")
        st.markdown("""
        This adaptive testing platform uses AI to:
        - Generate 20 questions from your study material
        - Show only 10 questions in the test with smart buffer usage
        - Adapt difficulty based on your performance  
        - Provide detailed learning analytics
        - Help identify knowledge gaps
        """)
    
    # Main content based on current page
    if st.session_state.page == 'upload':
        render_upload_page()
    elif st.session_state.page == 'test':
        render_test_page()
    elif st.session_state.page == 'results':
        render_results_page()

if __name__ == "__main__":
    main()
'''

with open("app.py", "w") as f:
    f.write(app_content)

print("✅ Created updated app.py with all fixes applied")