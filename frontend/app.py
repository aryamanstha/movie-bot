# streamlit_app.py
import streamlit as st
import requests
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="🎬 MovieBot",
    page_icon="🤖",
    layout="wide"  # Change layout to fullscreen
)

st.title("🎬 MovieBot: Your GraphQL Movie Assistant")
st.caption("I can help you find, add, update, or delete movies from the database using natural language.")

# --- Backend API URL ---
BACKEND_URL = "http://127.0.0.1:5000/chatbot"
BACKEND_GRAPHQL_URL = "http://127.0.0.1:5000/graphql" # New URL for direct GraphQL calls


def display_movie_card_html(movie):
    """Generates and displays a movie card using HTML and CSS."""
    if not isinstance(movie, dict):
        return

    # Extract movie details with fallbacks for N/A
    title = movie.get("Title", "N/A")
    year = movie.get("Year", "N/A")
    rating = movie.get("Rating", "N/A")
    runtime = movie.get("Runtime", "N/A")
    director = movie.get("Director", "N/A")
    actors = movie.get("Actors", "N/A")
    description = movie.get("Description", "N/A")

    # Define the HTML and CSS for the card
    html_card = f"""
    <div style="
        background-color: #262730; 
        padding: 20px; 
        border-radius: 10px; 
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); 
        margin-bottom: 20px;
        border: 1px solid #4B4B4B;
    ">
        <h3 style="color: #FF4B4B; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">{title}</h3>
        <hr style="border: none; border-top: 1px solid #4B4B4B; margin: 15px 0;">
        <div style="display: flex; justify-content: space-between; gap: 20px;">
            <div style="flex: 1; text-align: center;">
                <p style="margin: 0; color: #8C8C8C;">🗓️ Year</p>
                <h4 style="margin: 5px 0 0 0; color: #FFFFFF;">{year}</h4>
            </div>
            <div style="flex: 1; text-align: center;">
                <p style="margin: 0; color: #8C8C8C;">⭐ Rating</p>
                <h4 style="margin: 5px 0 0 0; color: #FFFFFF;">{rating}/10</h4>
            </div>
            <div style="flex: 1; text-align: center;">
                <p style="margin: 0; color: #8C8C8C;">⌛ Runtime</p>
                <h4 style="margin: 5px 0 0 0; color: #FFFFFF;">{runtime} min</h4>
            </div>
        </div>
        <hr style="border: none; border-top: 1px solid #4B4B4B; margin: 15px 0;">
        <p style="color: #FFFFFF; margin-bottom: 5px;">
            <strong style="color: #FF4B4B;">Directed by:</strong> {director}
        </p>
        <p style="color: #FFFFFF; margin-bottom: 5px;">
            <strong style="color: #FF4B4B;">Starring:</strong> {actors}
        </p>
        <p style="color: #B0B0B0;">{description}</p>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)


def find_and_update_movie_entry(new_data):
    """Finds and updates an existing movie entry in session state, or appends a new one."""
    title = new_data.get("Title")
    if not title:
        return None

    # Iterate backward to find the most recent message for this movie
    for message in reversed(st.session_state.messages):
        if message["role"] == "assistant" and message.get("data", {}).get("Title") == title:
            return message

    # If no existing entry is found, return None to indicate a new entry
    return None

def fetch_full_movie_details(title):
    """Fetches the full movie details from the backend using a direct GraphQL query."""
    query = """
        query getMovie($title: String!) {
            getMovie(title: $title) {
                Title
                Year
                Rating
                Runtime
                Description
                Director
                Actors
            }
        }
    """
    variables = {"title": title}
    try:
        response = requests.post(
            BACKEND_GRAPHQL_URL,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("data", {}).get("getMovie")
    except Exception as e:
        st.error(f"Failed to fetch full movie details: {e}")
        return None


# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            # Check the message type and render the appropriate UI
            if message["type"] == "movie_list":
                st.success("Here are the movies I found:")
                for movie in message["data"]:
                    display_movie_card_html(movie)
            elif message["type"] == "movie_single":
                st.success("Here is the movie you requested:")
                display_movie_card_html(message["data"])
            elif message["type"] == "create_success":
                st.success("Movie created successfully! Details are below:")
                display_movie_card_html(message["data"])
            elif message["type"] == "update_success":
                st.success("Movie updated successfully! Here are the new details:")
                display_movie_card_html(message["data"])
            elif message["type"] == "delete_success":
                st.success("Movie deleted successfully!")
            elif message["type"] == "info":
                st.info("I've processed your request. Here's the raw response:")
                st.json(message["data"])
            elif message["type"] == "error":
                st.error(message["content"])


# --- Chat Input and Logic ---
if prompt := st.chat_input("What would you like to do? (e.g., 'List all movies')"):
    # Add user's message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get the assistant's response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking... 🤔")
        print("printing prompt",prompt)
        try:
            # Call the backend API
            response = requests.post(BACKEND_URL, json={"query": prompt})
            response.raise_for_status()
            
            # Process the response
            api_response = response.json()
            result = api_response.get("result", {})
            data = result.get("data")
            
            # Remove the thinking message now that we have a response
            message_placeholder.empty()

            # --- Card Display Logic and Session State Update ---
            if data:
                if "listMovies" in data and data["listMovies"]:
                    st.success("Here are the movies I found:")
                    for movie in data["listMovies"]:
                        display_movie_card_html(movie)
                    st.session_state.messages.append({"role": "assistant", "type": "movie_list", "data": data["listMovies"]})
                elif "getMovie" in data and data["getMovie"]:
                    st.success("Here is the movie you requested:")
                    display_movie_card_html(data["getMovie"])
                    st.session_state.messages.append({"role": "assistant", "type": "movie_single", "data": data["getMovie"]})
                elif "createMovie" in data and data["createMovie"]:
                    st.success("Movie created successfully! Details are below:")
                    display_movie_card_html(data["createMovie"])
                    st.session_state.messages.append({"role": "assistant", "type": "create_success", "data": data["createMovie"]})
                elif "updateMovie" in data and data["updateMovie"]:
                    updated_movie_title = data["updateMovie"].get("Title")
                    if updated_movie_title:
                        # Fetch the full, updated movie details from the database
                        full_movie_data = fetch_full_movie_details(updated_movie_title)
                        
                        if full_movie_data:
                            # Update the existing message or append a new one
                            existing_message = find_and_update_movie_entry(full_movie_data)
                            if existing_message:
                                existing_message["type"] = "update_success"
                                existing_message["data"] = full_movie_data
                            else:
                                st.session_state.messages.append({"role": "assistant", "type": "update_success", "data": full_movie_data})
                            
                            st.success("Movie updated successfully! Here are the new details:")
                            display_movie_card_html(full_movie_data)
                        else:
                            st.error("Could not retrieve full movie details after update.")
                            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Could not retrieve full movie details after update."})
                    else:
                        st.error("Update failed. Could not find movie title in the response.")
                        st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Update failed. Could not find movie title in the response."})
                    
                elif "deleteMovie" in data and data.get("deleteMovie", {}).get("success"):
                    st.success("Movie deleted successfully!")
                    st.session_state.messages.append({"role": "assistant", "type": "delete_success", "content": "Movie deleted successfully!"})
                else:
                    st.info("I've processed your request. Here's the raw response:")
                    st.json(result)
                    st.session_state.messages.append({"role": "assistant", "type": "info", "data": result})
            else:
                st.error("There was an issue processing your request.")
                st.json(result)
                st.session_state.messages.append({"role": "assistant", "type": "error", "content": f"There was an issue: {result}"})
                
        except requests.exceptions.RequestException as e:
            error_message = f"**Error:** Could not connect to the backend. Please ensure the Flask server is running. \n\nDetails: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": error_message})
        except Exception as e:
            error_message = f"**An unexpected error occurred:** {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": error_message})