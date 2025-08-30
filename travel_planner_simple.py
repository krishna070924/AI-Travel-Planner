import os
import json
import re
from typing import List, Optional
from datetime import datetime, date, timedelta

import requests

# --- Hotel search (SerpAPI) -------------------------------------------------
def serpapi_search_hotels(destination, check_in, check_out, adults):
    serpapi_key = os.getenv("SERPAPI_KEY", "your-serpapi-key")
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": f"hotels in {destination}",
        "location": destination,
        "hl": "en",
        "gl": "us",
        "tbm": "lcl",
        "api_key": serpapi_key,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        hotels = []
        # Try local_results structures first
        if "local_results" in data:
            lr = data["local_results"]
            if isinstance(lr, list):
                hotels = lr
            elif isinstance(lr, dict) and "places" in lr:
                hotels = lr["places"]

        # Fallback: scan organic_results for hotel-like entries
        if not hotels and "organic_results" in data:
            for item in data["organic_results"]:
                title = item.get("title", "")
                if "hotel" in title.lower() or "inn" in title.lower():
                    hotels.append({
                        "title": item.get("title", "N/A"),
                        "address": item.get("address", "N/A"),
                        "rating": item.get("rating", "N/A"),
                        "reviews": item.get("reviews", "N/A"),
                        "price": item.get("price", "N/A"),
                        "link": item.get("link", "N/A"),
                    })

        if not hotels:
            debug_info = f"\n\n<details><summary>Debug: Raw SerpAPI response</summary>\n<pre>{json.dumps(data, indent=2)[:2000]}...</pre></details>"
            return "No hotels found for your search." + debug_info

        result = "### Top Hotels (Google Hotels via SerpAPI)\n"
        result += "| Name | Address | Rating | Reviews | Price | Link |\n"
        result += "|---|---|---|---|---|---|\n"
        for h in hotels[:5]:
            name = h.get("title", "N/A")
            address = h.get("address", "N/A")
            rating = h.get("rating", "N/A")
            reviews = h.get("reviews", "N/A")
            price = h.get("price", "N/A")
            link = h.get("link") or "N/A"
            if link != "N/A":
                link = f"[View]({link})"
            result += f"| {name} | {address} | {rating} | {reviews} | {price} | {link} |\n"
        return result
    except Exception as e:
        return f"[SerpAPI error: {e}]"


# --- Flight helpers (Aerodatabox via RapidAPI) -----------------------------
def get_iata_code(city_name: str) -> str:
    """Try to resolve a city name to an IATA code via Aerodatabox; if it fails return input."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return city_name
    url = f"https://aerodatabox.p.rapidapi.com/airports/search/term/{city_name}?limit=1"
    headers = {
        "x-rapidapi-host": "aerodatabox.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if items:
            return items[0].get("iata") or city_name
    except Exception:
        pass
    return city_name


def fetch_realtime_flights(origin, destination, departure_date, return_date, adults):
    """Fetch real-time flight data from Aerodatabox. Falls back to a small mock if unavailable."""
    api_key = os.getenv("RAPIDAPI_KEY")
    origin_iata = get_iata_code(origin)
    dest_iata = get_iata_code(destination)
    if not api_key:
        return mock_search_flights(origin, destination, departure_date, return_date, adults)

    url = (
        f"https://aerodatabox.p.rapidapi.com/flights/airports/iata/{origin_iata}"
        "?offsetMinutes=-120&durationMinutes=720&withLeg=true&direction=Both&withCancelled=true"
        "&withCodeshared=true&withCargo=true&withPrivate=true&withLocation=false"
    )
    headers = {
        "x-rapidapi-host": "aerodatabox.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        flights = data.get("departures", [])
        if not flights:
            return "No real-time flights found."

        def nested_get(d, *path):
            cur = d
            for p in path:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(p)
                if cur is None:
                    return None
            return cur

        def get_arrival_iata(f):
            return (
                nested_get(f, "arrival", "airport", "iata")
                or nested_get(f, "arrival", "iata")
                or nested_get(f, "arrivalIata")
            )

        filtered = [f for f in flights if get_arrival_iata(f) == dest_iata]
        if not filtered:
            filtered = flights[:5]

        result = f"### Real-time flights from {origin_iata} to {dest_iata} on {departure_date}\n"
        result += "| Airline | Flight | Departure | Departure Airport | Arrival | Arrival Airport | Duration | Status | Terminal | Gate | Aircraft | Baggage |\n"
        result += "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        meaningful = 0
        for f in filtered[:5]:
            airline = nested_get(f, "airline", "name") or f.get("airlineName") or nested_get(f, "operatingAirline", "name") or "N/A"
            flight_num = f.get("flightNumber") or f.get("number") or nested_get(f, "flight", "number") or "N/A"
            dep_time = (
                nested_get(f, "scheduledTimeLocal")
                or nested_get(f, "departure", "scheduledTimeLocal")
                or nested_get(f, "departure", "actualTimeLocal")
                or "N/A"
            )
            dep_airport = (
                nested_get(f, "airport", "name")
                or nested_get(f, "departure", "airport", "name")
                or nested_get(f, "departure", "airportName")
                or "N/A"
            )
            arr_time = nested_get(f, "arrival", "scheduledTimeLocal") or nested_get(f, "arrival", "actualTimeLocal") or "N/A"
            arr_airport = nested_get(f, "arrival", "airport", "name") or nested_get(f, "arrival", "airportName") or "N/A"
            duration = f.get("flightDuration") or nested_get(f, "duration") or "N/A"
            status = f.get("status") or nested_get(f, "status", "name") or "N/A"
            terminal = f.get("terminal") or nested_get(f, "departure", "terminal") or nested_get(f, "arrival", "terminal") or "N/A"
            gate = f.get("gate") or nested_get(f, "departure", "gate") or nested_get(f, "arrival", "gate") or "N/A"
            aircraft = nested_get(f, "aircraft", "model") or f.get("aircraftModel") or nested_get(f, "aircraft", "type") or "N/A"
            baggage = f.get("baggageBelt") or nested_get(f, "arrival", "baggageBelt") or "N/A"

            meaningful = sum(1 for v in [airline, flight_num, dep_time, dep_airport, arr_time, arr_airport, aircraft] if v and v != "N/A")
            result += f"| {airline} | {flight_num} | {dep_time} | {dep_airport} | {arr_time} | {arr_airport} | {duration} | {status} | {terminal} | {gate} | {aircraft} | {baggage} |\n"

        if meaningful < 3:
            result += "\n> Note: The flight API response is missing many fields; try updating your RapidAPI key or check the API quota."

        return result
    except Exception as e:
        return f"[API error: {e}] Falling back to mock data.\n" + mock_search_flights(origin, destination, departure_date, return_date, adults)


def mock_search_flights(origin, destination, departure_date, return_date, adults):
    return (
        f"Flights from {origin} to {destination} on {departure_date}{' returning ' + return_date if return_date else ''} for {adults} adults:\n"
        "- Airline X: $350\n- Airline Y: $420\n- Airline Z: $390"
    )


# --- LangChain optional integration ---------------------------------------
try:
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferMemory
    from langchain.llms.base import LLM
    LANGCHAIN_PRESENT = True
except Exception:
    LANGCHAIN_PRESENT = False


def get_mistral_client():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise Exception("MISTRAL_API_KEY not set.")
    from mistralai.client import MistralClient
    return MistralClient(api_key=api_key)


def get_mistral_llm():
    """Simple callable wrapper around the mistralai client for backward compatibility."""
    client = get_mistral_client()

    class MistralLLMCallable:
        def __init__(self, client):
            self.client = client

        def __call__(self, prompt, **kwargs):
            response = self.client.chat(
                model=kwargs.get("model", "mistral-tiny"),
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.7),
            )
            try:
                return response.choices[0].message.content
            except Exception:
                return getattr(response, "content", str(response))

    return MistralLLMCallable(client)


if LANGCHAIN_PRESENT:
    class MistralLangChainLLM(LLM):
        def __init__(self, client, model: str = "mistral-tiny"):
            self.client = client
            self.model = model

        def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            try:
                return response.choices[0].message.content
            except Exception:
                return getattr(response, "content", str(response))

        @property
        def _identifying_params(self):
            return {"model": self.model}

        @property
        def _llm_type(self):
            return "mistral_shim"


    def get_langchain_llm():
        client = get_mistral_client()
        return MistralLangChainLLM(client)


def get_llm():
    # Prefer a LangChain-compatible LLM when LangChain is installed
    if LANGCHAIN_PRESENT:
        try:
            return get_langchain_llm()
        except Exception:
            pass
    return get_mistral_llm()


def get_mistral_insights(destination, duration, budget, interests):
    llm = get_mistral_llm()
    prompt = (
        f"You are a travel expert. Create comprehensive travel insights for a trip to {destination} "
        f"for {duration} with a {budget} budget. Interests: {interests}.\n"
        "Respond in markdown with:\n- Top attractions\n- Local tips\n- Best time to visit\n- Estimated daily budget\n- Safety and cultural notes\n"
    )
    return llm(prompt)


# --- Data models and planner -----------------------------------------------
class TravelItinerary:
    def __init__(self, destination, duration, total_budget, days, additional_tips, hotels=None, flights=None):
        self.destination = destination
        self.duration = duration
        self.total_budget = total_budget

        class DayPlan:
            def __init__(self, day, activities, meals, accommodation, budget_estimate):
                self.day = day
                self.activities = activities
                self.meals = meals
                self.accommodation = accommodation
                self.budget_estimate = budget_estimate

            def to_dict(self):
                return {
                    "day": self.day,
                    "activities": self.activities,
                    "meals": self.meals,
                    "accommodation": self.accommodation,
                    "budget_estimate": self.budget_estimate,
                }

        normalized_days = []
        for d in (days or []):
            if isinstance(d, dict):
                normalized_days.append(DayPlan(
                    day=d.get("day"),
                    activities=d.get("activities", []),
                    meals=d.get("meals", []),
                    accommodation=d.get("accommodation", ""),
                    budget_estimate=d.get("budget_estimate", ""),
                ))
            else:
                normalized_days.append(d)

        self.days = normalized_days
        self.additional_tips = additional_tips
        self.hotels = hotels
        self.flights = flights

    def dict(self):
        return {
            "destination": self.destination,
            "duration": self.duration,
            "total_budget": self.total_budget,
            "days": [d.to_dict() if hasattr(d, 'to_dict') else d for d in self.days],
            "additional_tips": self.additional_tips,
            "hotels": self.hotels,
            "flights": self.flights,
        }


class TravelPlanner:
    def __init__(self):
        try:
            self.llm = get_llm()
        except Exception:
            self.llm = None

        self.chain = None
        self.memory = None
        if LANGCHAIN_PRESENT and self.llm is not None:
            try:
                template = (
                    "You are a travel expert. Create a detailed travel itinerary as JSON for a trip to {destination} "
                    "for {duration} with a {budget} budget. Interests: {interests}.\n"
                    "Return strictly valid JSON with keys: destination, duration, total_budget, days (list of objects with day, activities, meals, accommodation, budget_estimate), additional_tips."
                )
                prompt = PromptTemplate(template=template, input_variables=["destination", "duration", "budget", "interests"])
                self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=False)
                self.chain = LLMChain(llm=self.llm, prompt=prompt, memory=self.memory)
            except Exception:
                self.chain = None
                self.memory = None

    def generate_itinerary(self, destination, duration, budget, interests):
        # Use LangChain LLMChain when available
        if self.chain:
            try:
                output = self.chain.run({
                    "destination": destination,
                    "duration": duration,
                    "budget": budget,
                    "interests": interests,
                })
                try:
                    data = json.loads(output)
                except Exception:
                    m = re.search(r"\{.*\}", output, re.DOTALL)
                    if m:
                        data = json.loads(m.group(0))
                    else:
                        data = None
            except Exception:
                data = None
        else:
            if self.llm:
                prompt = (
                    f"You are a travel expert. Create a detailed travel itinerary for a trip to {destination} for {duration} with a {budget} budget. Interests: {interests}.\n"
                    "Respond in JSON with fields: destination, duration, total_budget, days (list), additional_tips."
                )
                try:
                    output = self.llm(prompt)
                    try:
                        data = json.loads(output)
                    except Exception:
                        m = re.search(r"\{.*\}", output, re.DOTALL)
                        data = json.loads(m.group(0)) if m else None
                except Exception:
                    data = None
            else:
                data = None

        if not data:
            days = [{
                "day": i + 1,
                "activities": [f"Sightseeing in {destination}", "Local meal"],
                "meals": ["Breakfast", "Lunch", "Dinner"],
                "accommodation": "Central hotel",
                "budget_estimate": "$50-$150",
            } for i in range(3)]
            hotels = None
            flights = None
            try:
                hotels = serpapi_search_hotels(destination, date.today().strftime("%Y-%m-%d"), (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"), adults=2)
            except Exception:
                hotels = None
            try:
                flights = fetch_realtime_flights("YourCity", destination, date.today().strftime("%Y-%m-%d"), None, adults=1)
            except Exception:
                flights = None
            return TravelItinerary(destination, duration, "$150-450", days, ["Carry a reusable water bottle."], hotels=hotels, flights=flights)

        hotels = None
        flights = None
        try:
            hotels = serpapi_search_hotels(destination, date.today().strftime("%Y-%m-%d"), (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"), adults=2)
        except Exception:
            hotels = None
        try:
            flights = fetch_realtime_flights("YourCity", destination, date.today().strftime("%Y-%m-%d"), None, adults=1)
        except Exception:
            flights = None

        return TravelItinerary(
            destination=data.get("destination", destination),
            duration=data.get("duration", duration),
            total_budget=data.get("total_budget", "$150-450"),
            days=data.get("days", []),
            additional_tips=data.get("additional_tips", []),
            hotels=hotels,
            flights=flights,
        )

    def search_hotels(self, destination, check_in, check_out, adults):
        return serpapi_search_hotels(destination, check_in, check_out, adults)

    def search_flights(self, origin, destination, departure_date, return_date, adults):
        return fetch_realtime_flights(origin, destination, departure_date, return_date, adults)

    def chat(self, prompt):
        chat_prompt = f"You are a helpful travel assistant. Answer the user's question about travel.\nUser: {prompt}\nAssistant:"
        if not self.llm:
            return "I can't access the AI right now, but I can help with basic travel info."
        try:
            return self.llm(chat_prompt)
        except Exception:
            return "I can't access the AI right now, but I can help with basic travel info."

    def get_travel_recommendations(self, query):
        tips_prompt = f"Give concise travel tips or recommendations for: {query}"
        if not self.llm:
            return "Pack light, check local weather, and keep digital copies of your documents."
        return self.llm(tips_prompt)


# Singleton instance for app.py
travel_planner = TravelPlanner()
