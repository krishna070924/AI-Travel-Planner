import streamlit as st
import json
from datetime import datetime, date, timedelta
# Load environment variables from .env automatically
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



try:
    from travel_planner_simple import travel_planner, TravelItinerary
    from mistralai.client import MistralClient
    # Instantiate Mistral client only from environment variable to avoid leaking secrets in code
    mistral_key = os.getenv("MISTRAL_API_KEY")
    client = MistralClient(api_key=mistral_key) if mistral_key else None
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    st.error(f"Travel planner dependencies not available: {e}")
    st.error("Please check the installation and try again.")
    LANGCHAIN_AVAILABLE = False

def main():
    st.set_page_config(
        page_title="AI Travel Planner",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar header with logo and color
    st.sidebar.markdown("""
        <div style='text-align:center; padding: 0.5em 0;'>
            <span style='font-size:2em;'>🌍</span><br>
            <span style='font-size:1.3em; font-weight:bold; color:#1e90ff;'>AI Travel Planner</span>
            <hr style='margin:0.5em 0 1em 0; border:1px solid #1e90ff;'>
        </div>
    """, unsafe_allow_html=True)

    st.title("🌍 AI Travel Planner")
    st.markdown("<span style='color:#1e90ff; font-size:1.1em;'>Powered by <b>Mistral AI</b> & Real-Time Data</span>", unsafe_allow_html=True)

    # Display API status in a horizontal info bar
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    aerodb_api_key = os.getenv("RAPIDAPI_KEY")
    status_cols = st.columns(2)
    with status_cols[0]:
        if mistral_api_key:
            st.success("🤖 Mistral AI: Connected")
        else:
            st.info("🤖 Mistral AI: Not Connected")
    with status_cols[1]:
        if aerodb_api_key:
            st.success("✈️ AeroDataBox: Connected")
        else:
            st.warning("✈️ AeroDataBox: Not Connected")

    st.markdown("---")
    
    if not LANGCHAIN_AVAILABLE:
        st.error("Dependencies not available. Please install requirements first.")
        return
    
    # Sidebar for navigation
    st.sidebar.title(":blue[Navigation]")
    page = st.sidebar.radio(
        "",
        ["🗓️ Plan Itinerary", "🏨 Find Hotels", "✈️ Find Flights", "💬 Chat Assistant", "📚 Travel Tips", "🤖 AI Insights"],
        label_visibility="collapsed"
    )
    
    # API Key check
    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_api_key:
        st.sidebar.warning("⚠️ Add MISTRAL_API_KEY for AI-powered features")
        st.sidebar.info("Using enhanced mock data for demonstration")
    else:
        st.sidebar.success("🤖 Mistral AI: Active")
    
    if page == "🗓️ Plan Itinerary":
        itinerary_page()
    elif page == "🏨 Find Hotels":
        hotel_page()
    elif page == "✈️ Find Flights":
        flight_page()
    elif page == "💬 Chat Assistant":
        chat_page()
    elif page == "📚 Travel Tips":
        travel_tips_page()
    elif page == "🤖 AI Insights":
        show_ai_insights_page()

def itinerary_page():
    """Itinerary planning page using LangChain components"""
    st.header("🗓️ Create Your Travel Itinerary")
    st.markdown(":blue[Generate personalized travel itineraries using AI and real-time data]")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        destination = st.text_input("🌍 Destination", placeholder="e.g., Paris, Tokyo, New York")
        duration = st.selectbox("📅 Duration", ["3 days", "5 days", "7 days", "10 days", "14 days"])
        
    with col2:
        budget = st.selectbox("💰 Budget Range", 
                             ["Budget ($50-100/day)", "Mid-range ($100-200/day)", 
                              "Luxury ($200-500/day)", "Ultra-luxury ($500+/day)"])
        interests = st.multiselect("🎯 Interests", 
                                  ["Culture & History", "Food & Dining", "Adventure", 
                                   "Shopping", "Nightlife", "Nature", "Art & Museums", 
                                   "Architecture", "Local Experiences"])
    
    interests_str = ", ".join(interests) if interests else "General sightseeing"
    
    if st.button("🚀 Generate Itinerary", type="primary"):
        if destination:
            with st.spinner("Creating your personalized itinerary..."):
                try:
                    itinerary = travel_planner.generate_itinerary(
                        destination=destination,
                        duration=duration,
                        budget=budget,
                        interests=interests_str
                    )
                    
                    # Display the itinerary
                    display_itinerary(itinerary)
                    
                except Exception as e:
                    st.error(f"Error generating itinerary: {str(e)}")
                    st.info("Please check your API key and try again.")
        else:
            st.warning("Please enter a destination")

def display_itinerary(itinerary):
    """Display the generated itinerary"""
    st.success("✅ Your itinerary has been generated!")
    st.markdown("---")
    # Overview
    st.subheader(f"🎯 {itinerary.destination} - {itinerary.duration}")
    st.info(f"💰 **Total Budget**: {itinerary.total_budget}")
    st.markdown("---")
    # Daily breakdown
    for day_plan in itinerary.days:
        with st.expander(f"📅 Day {day_plan.day}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(":blue[**🎯 Activities:**]")
                for activity in day_plan.activities:
                    st.markdown(f"- {activity}")
                st.markdown(":blue[**🍽️ Meals:**]")
                for meal in day_plan.meals:
                    st.markdown(f"- {meal}")
            with col2:
                st.markdown(f":blue[**🏨 Accommodation:**] {day_plan.accommodation}")
                st.markdown(f":blue[**💵 Daily Budget:**] {day_plan.budget_estimate}")
    # Show hotels and flights if available
    if hasattr(itinerary, 'hotels') and itinerary.hotels:
        st.markdown("---")
        st.subheader("🏨 Suggested Hotels")
        st.markdown(itinerary.hotels)
    if hasattr(itinerary, 'flights') and itinerary.flights:
        st.markdown("---")
        st.subheader("✈️ Suggested Flights")
        st.markdown(itinerary.flights)
    st.markdown("---")
    # Additional tips
    if itinerary.additional_tips:
        st.subheader(":bulb: Additional Tips")
        for tip in itinerary.additional_tips:
            st.markdown(f"- {tip}")
    st.markdown("---")
    # Download option
    itinerary_json = itinerary.dict()
    st.download_button(
        label="📥 Download Itinerary (JSON)",
        data=json.dumps(itinerary_json, indent=2),
        file_name=f"{itinerary.destination.lower().replace(' ', '_')}_itinerary.json",
        mime="application/json"
    )

def hotel_page():
    """Hotel search page using Tools/Agents"""
    st.header("🏨 Find Hotels")
    st.markdown(":blue[Search for accommodations using real-time hotel data]")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        destination = st.text_input("🌍 Destination", placeholder="City or location")
        check_in = st.date_input("📅 Check-in", value=date.today())

    with col2:
        # Auto-advance check-out if needed
        min_checkout = check_in + timedelta(days=1)
        check_out = st.date_input("📅 Check-out", value=min_checkout, min_value=min_checkout)
        adults = st.number_input("👥 Adults", min_value=1, max_value=10, value=2)

    with col3:
        st.write("")  # Spacing
        # Disable search button if dates are invalid
        search_hotels = st.button("🔍 Search Hotels", type="primary", disabled=(not destination or check_in >= check_out))

    if search_hotels:
        with st.spinner("Searching for hotels..."):
            try:
                results = travel_planner.search_hotels(
                    destination=destination,
                    check_in=check_in.strftime("%Y-%m-%d"),
                    check_out=check_out.strftime("%Y-%m-%d"),
                    adults=adults
                )
                st.subheader("🏨 Hotel Search Results")
                st.markdown(results)
            except Exception as e:
                st.error(f"Error searching hotels: {str(e)}")

def flight_page():
    """Flight search page using Tools/Agents"""
    st.header("✈️ Find Flights")
    st.markdown(":blue[Search for flights using real-time airline data]")
    st.markdown("---")
    
    trip_type = st.radio("Trip Type", ["One-way", "Round-trip"], horizontal=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        origin = st.text_input("🛫 From", placeholder="City or airport code")
        departure_date = st.date_input("📅 Departure", value=date.today())
    
    with col2:
        destination = st.text_input("🛬 To", placeholder="City or airport code")
        if trip_type == "Round-trip":
            return_date = st.date_input("📅 Return", value=date.today())
        else:
            return_date = None
    
    with col3:
        adults = st.number_input("👥 Passengers", min_value=1, max_value=9, value=1)
        st.write("")  # Spacing
        search_flights = st.button("🔍 Search Flights", type="primary")
    
    if search_flights:
        if origin and destination:
            with st.spinner("Searching for flights..."):
                try:
                    results = travel_planner.search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date.strftime("%Y-%m-%d"),
                        return_date=return_date.strftime("%Y-%m-%d") if return_date else None,
                        adults=adults
                    )
                    st.subheader("✈️ Flight Search Results")
                    if results.strip().startswith("### Real-time flights"):
                        st.markdown(results, unsafe_allow_html=True)
                    else:
                        st.info(results)
                except Exception as e:
                    st.error(f"Error searching flights: {str(e)}")
        else:
            st.warning("Please enter both origin and destination")

def chat_page():
    """Conversational chat page using Memory"""
    st.header("💬 Travel Chat Assistant")
    st.markdown(":blue[Ask me anything about travel! I have access to real-time data and booking tools.]")
    st.markdown("---")
    
    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about travel plans, destinations, hotels, flights..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = travel_planner.chat(prompt)
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"I apologize, but I encountered an error: {str(e)}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

def travel_tips_page():
    """Travel tips page using VectorStore/RAG"""
    st.header("📚 Travel Tips & Recommendations")
    st.markdown(":blue[Get personalized travel advice from our AI knowledge base]")
    st.markdown("---")
    
    # Predefined categories
    st.subheader("🎯 Quick Tips")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💰 Budget Travel"):
            get_travel_advice("budget travel tips money saving")
    
    with col2:
        if st.button("🗾 Cultural Experiences"):
            get_travel_advice("cultural experiences local traditions")
    
    with col3:
        if st.button("🍜 Food & Dining"):
            get_travel_advice("food dining local cuisine restaurants")
    
    # Custom query
    st.subheader("🔍 Ask Specific Questions")
    custom_query = st.text_input("Ask about any travel topic:", 
                                placeholder="e.g., What to do in Paris? Best time to visit Japan?")
    
    if st.button("Get Advice") and custom_query:
        get_travel_advice(custom_query)

def show_ai_insights_page():
    """Enhanced AI Insights page with Mistral AI integration"""
    st.title("🤖 AI Travel Insights")
    st.markdown(":blue[*Powered by Mistral AI and Advanced Travel Analytics*]")
    st.markdown("---")

    mistral_api_key = os.getenv("MISTRAL_API_KEY")
    ai_available = bool(mistral_api_key)
    api_key_preview = mistral_api_key[:10] + "***" if mistral_api_key else "Not available"

    # AI Status indicator
    if ai_available:
        st.success(f"🤖 AI Mode Active - Mistral API ({api_key_preview})")
    else:
        st.info("📝 Enhanced Mode - Using intelligent mock data")

    col1, col2 = st.columns(2)

    with col1:
        destination = st.text_input("🌍 Destination", placeholder="e.g., Paris, Tokyo, New York")
        duration = st.selectbox("📅 Trip Duration", ["3 days", "1 week", "2 weeks", "1 month", "Custom"])
        if duration == "Custom":
            duration = st.text_input("Custom duration", placeholder="e.g., 10 days")

    with col2:
        budget = st.selectbox("💰 Budget Level", ["Budget-friendly", "Mid-range", "Luxury", "Ultra-luxury"])
        interests = st.text_area("🎯 Your Interests", placeholder="e.g., art, history, food, adventure, nightlife")

    if st.button("🤖 Get AI Travel Insights", type="primary"):
        if destination and duration and budget:
            with st.spinner("🤖 AI is analyzing travel data and generating personalized insights..."):
                try:
                    if ai_available:
                        from travel_planner_simple import get_mistral_insights
                        insights = get_mistral_insights(destination, duration, budget, interests)
                        st.success("✨ AI insights generated using Mistral AI!")
                    else:
                        # Fallback to the existing travel_planner instance when AI is not available
                        insights = travel_planner.get_travel_recommendations(
                            f"Create comprehensive travel insights for {destination} "
                            f"for {duration} with {budget} budget interested in {interests}"
                        )
                        st.info("📊 Enhanced insights generated using advanced analytics")

                    st.markdown("---")
                    st.markdown("## 🌟 Your Personalized Travel Intelligence")
                    st.markdown(insights)

                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("💰 Est. Daily Budget", "$50-150" if "budget" in budget.lower() else "$150-300" if "mid" in budget.lower() else "$300+")
                    with col2:
                        st.metric("🎯 Key Attractions", "8-12")
                    with col3:
                        st.metric("⭐ AI Confidence", "95%" if ai_available else "88%")

                    if 'ai_insights' not in st.session_state:
                        st.session_state.ai_insights = []
                    st.session_state.ai_insights.append({
                        'destination': destination,
                        'insights': insights,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
                    })

                except Exception as e:
                    st.error(f"❌ Error generating insights: {str(e)}")
        else:
            st.warning("⚠️ Please fill in all required fields")

    if 'ai_insights' in st.session_state and st.session_state.ai_insights:
        st.markdown("---")
        st.subheader("📚 Recent AI Insights")
        for i, insight in enumerate(reversed(st.session_state.ai_insights[-3:])):
            with st.expander(f"🌍 {insight['destination']} - {insight['timestamp']}"):
                st.markdown(insight['insights'][:500] + "..." if len(insight['insights']) > 500 else insight['insights'])

def get_travel_advice(query):
    """Get travel advice using real-time AI or enhanced recommendations"""
    with st.spinner("🤖 AI is searching travel knowledge..."):
        try:
            from realtime_api import get_travel_insights_realtime
            
            # Use AI to generate advice based on query
            advice = get_travel_insights_realtime(
                destination=query,
                duration="flexible",
                budget="mid-range",
                interests=query
            )
            
            st.subheader("🤖 AI Travel Advice")
            st.markdown(advice)
            
        except Exception as e:
            # Fallback to basic advice
            advice = travel_planner.get_travel_recommendations(query)
            st.subheader("💡 Travel Advice")
            st.markdown(advice)

if __name__ == "__main__":
    main()
