import json
import os
from flask import Flask, request, jsonify
from ariadne import gql, QueryType, MutationType, make_executable_schema, graphql_sync
from ariadne.explorer import ExplorerGraphiQL
import requests

# --- Initial Setup ---
app = Flask(__name__)
DATA_FILE = "imdb.json"
OLLAMA_API_URL = "http://127.0.0.1:11434/api/chat"

# --- Data Handling Functions ---
def load_movies_from_db():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_movies_to_db(movies):
    with open(DATA_FILE, 'w') as f:
        json.dump(movies, f, indent=4)

movies_db = load_movies_from_db()
print(f"Loaded {len(movies_db)} movies from {DATA_FILE}")

# --- GraphQL Schema Definition (SDL) ---
type_defs = gql("""
    type Movie {
        Ids: Int!
        Title: String!
        Genre: String
        Description: String
        Director: String
        Actors: String
        Year: Int
        Runtime: Int
        Rating: Float
        Votes: Int
        Revenue: Float
    }

    input MovieInput {
        Title: String!
        Genre: String
        Description: String
        Director: String
        Actors: String
        Year: Int
        Runtime: Int
        Rating: Float
        Votes: Int
        Revenue: Float
    }

    input UpdateMovieInput {
        Genre: String
        Description: String
        Director: String
        Actors: String
        Year: Int
        Runtime: Int
        Rating: Float
        Votes: Int
        Revenue: Float
    }

    input MovieFilterInput {
        titleContains: String!
        minRating: Float
        minYear: Int
        maxYear: Int
        exactYear: Int
        genreContains: String
        directorContains: String
        actorContains: String
        minRuntime: Int
        maxRuntime: Int
    }

    type DeletePayload {
        success: Boolean!
        message: String
    }

    type Query {
        listMovies(
            filter: MovieFilterInput,
            limit: Int,
            sortBy: String,
            order: String
        ): [Movie!]
        getMovie(title: String!): Movie
    }

    type Mutation {
        createMovie(input: MovieInput!): Movie
        updateMovie(title: String!, input: UpdateMovieInput!): Movie
        deleteMovie(title: String!): DeletePayload
    }
""")

# --- Resolvers ---
query = QueryType()
mutation = MutationType()

@query.field("listMovies")
def resolve_list_movies(_, info, filter=None, limit=None, sortBy=None, order="ASC"):
    filtered_movies = movies_db

    if filter:
        if "titleContains" in filter:
            term = filter["titleContains"].lower()
            filtered_movies = [m for m in filtered_movies if m.get("Title") and m["Title"].lower() == term]
        if "minRating" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Rating") and m["Rating"] >= filter["minRating"]]
        if "minYear" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Year") and m["Year"] >= filter["minYear"]]
        if "maxYear" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Year") and m["Year"] <= filter["maxYear"]]
        if "exactYear" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Year") == filter["exactYear"]]
        if "minRuntime" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Runtime") and m["Runtime"] >= filter["minRuntime"]]
        if "maxRuntime" in filter:
            filtered_movies = [m for m in filtered_movies if m.get("Runtime") and m["Runtime"] <= filter["maxRuntime"]]
        if "genreContains" in filter:
            term = filter["genreContains"].lower()
            filtered_movies = [m for m in filtered_movies if m.get("Genre") and term in m["Genre"].lower()]
        if "directorContains" in filter:
            term = filter["directorContains"].lower()
            filtered_movies = [m for m in filtered_movies if m.get("Director") and term in m["Director"].lower()]
        if "actorContains" in filter:
            term = filter["actorContains"].lower()
            filtered_movies = [m for m in filtered_movies if m.get("Actors") and term in m["Actors"].lower()]

    # Sorting
    if sortBy:
        reverse = True if order and order.upper() == "DESC" else False
        filtered_movies = sorted(filtered_movies, key=lambda m: m.get(sortBy) or 0, reverse=reverse)

    # # Apply limit
    # if limit:
    #     return filtered_movies[:limit]
    
    if not filtered_movies:
        return [{"Title": "No movies found", "Year": None, "Rating": None, "Runtime": None, "Description": "No movies matched your criteria", "Director": None, "Actors": None}]

    return filtered_movies

@query.field("getMovie")
def resolve_get_movie(_, info, title):
    movie = next((m for m in movies_db if m['Title'].lower() == title.lower()), None)
    if not movie:
        return {"Title": "No movie found", "Year": None, "Rating": None, "Runtime": None, "Description": f"No movie with title '{title}' was found", "Director": None, "Actors": None}
    return movie

@mutation.field("createMovie")
def resolve_create_movie(_, info, input):
    if any(m['Title'].lower() == input['Title'].lower() for m in movies_db):
        raise Exception(f"Movie with title '{input['Title']}' already exists.")
    new_id = max([m['Ids'] for m in movies_db]) + 1 if movies_db else 1
    new_movie = {**input, "Ids": new_id}
    movies_db.append(new_movie)
    save_movies_to_db(movies_db)
    return new_movie

@mutation.field("updateMovie")
def resolve_update_movie(_, info, title, input):
    movie_to_update = next((m for m in movies_db if m['Title'].lower() == title.lower()), None)
    if not movie_to_update:
        raise Exception(f"Movie with title '{title}' not found.")
    for key, value in input.items():
        if value is not None:
            movie_to_update[key] = value
    save_movies_to_db(movies_db)
    return movie_to_update

@mutation.field("deleteMovie")
def resolve_delete_movie(_, info, title):
    global movies_db
    initial_count = len(movies_db)
    movies_db = [m for m in movies_db if m['Title'].lower() != title.lower()]
    if len(movies_db) < initial_count:
        save_movies_to_db(movies_db)
        return {"success": True, "message": f"Movie '{title}' was deleted successfully."}
    return {"success": False, "message": f"Movie '{title}' not found."}

schema = make_executable_schema(type_defs, query, mutation)
explorer = ExplorerGraphiQL()

@app.route("/graphql", methods=["GET"])
def graphql_playground():
    return explorer.html(None), 200

@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(schema, data, context_value=request, debug=app.debug)
    status_code = 200 if success else 400
    return jsonify(result), status_code

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    prompt = f"""
    You are an expert AI that converts natural language text into GraphQL queries.
    Based on the schema below, generate a GraphQL query or mutation that corresponds to the user's request.
    You must ONLY return the GraphQL query or mutation, with no other text, explanation, or markdown.

    --- SCHEMA ---
    {type_defs}
    --- END SCHEMA ---

    Examples:
    - User: "show me all movies"
    - AI: query {{ listMovies {{ Ids Title Year }} }}

    - User: "find movies with rating greater than 8.5"
    - AI: query {{ listMovies(filter: {{minRating: 8.5}}) {{ Title Rating }} }}
    
    - User: "List 3 action movies"
    - AI: query {{ listMovies(filter: {{genreContains: "Action"}}, limit: 3) {{ Title Genre }} }}

    - User: "Show me movies released after 2020"
    - AI: query {{ listMovies(filter: {{minYear: 2021}}) {{ Title Year }} }}

    - User: "List movies from before the year 2000"
    - AI: query {{ listMovies(filter: {{maxYear: 1999}}) {{ Title Year }} }}

    - User: "tell me about the movie Prometheus"
    - AI: query {{ getMovie(title: "Prometheus") {{ Title Year Rating Runtime Description Director Actors }} }}

    - User: "delete the movie Suicide Squad"
    - AI: mutation {{ deleteMovie(title: "Suicide Squad") {{ success message }} }}
    
    - User: "update the movie Aryaman with year 2025"
    - AI: mutation {{ updateMovie(title: "Aryaman", input: {{ Year: 2025 }}) {{ Title Year }} }}
    
    - User: "show me the top 5 highest rated movies"
    - AI: query {{ listMovies(sortBy: "Rating", order: "DESC", limit: 5) {{ Title Year Rating Runtime Description Director Actors }} }}
    
    - User: "find the movie the dark knight"
    - AI: query {{ getMovie(title: "The Dark Knight") {{ Title Year Rating Runtime Description Director Actors }} }}

    - User: "find all Christopher Nolan movies"
    - AI: query {{ listMovies(filter: {{directorContains: "Christopher Nolan"}}) {{ Title Year Rating Runtime Description Director Actors }} }}

    - User: "get movies that feature Leonardo DiCaprio"
    - AI: query {{ listMovies(filter: {{actorContains: "Leonardo DiCaprio"}}) {{ Title Year Rating Runtime Description Director Actors }} }}

    - User: "list comedy movies released in 2015"
    - AI: query {{ listMovies(filter: {{genreContains: "Comedy", exactYear: 2015}}) {{ Title Year Rating Runtime Description Director Actors }} }}

    - User: "show me movies shorter than 100 minutes"
    - AI: query {{ listMovies(filter: {{maxRuntime: 100}}) {{ Title Year Rating Runtime Description Director Actors }} }}

    Important:
    - Always normalize user input for titles (case-insensitive allowed) when using getMovie, listMovies, updateMovie or deleteMovie.
    -If the user requests any movie by title (case-insensitive allowed) using prompts like 'show me...', 'find...', 'tell me about...', always use getMovie.
    - If the user requests multiple movies, always use listMovies with appropriate filters.
    -If the user requests a specific movie to be deleted, always use deleteMovie.
    - If the user requests a specific movie to be updated, always use updateMovie.
    - If the user requests a new movie to be added, always use createMovie.
    - If the user requests sorting, use sortBy and order parameters in listMovies.
    - If the user requests a limit on the number of results, use the limit parameter in listMovies.
    - If the user requests filtering based on rating, year, genre, director, actors, or runtime, use the filter parameter in listMovies.
    -If there is a spelling mistake in the movie title, correct it to the best of your ability.
    -If listMovies or getMovie produces an empty list provide the response that no result is found.
    - Always ensure the generated GraphQL query or mutation is syntactically correct.
    
    - When generating queries for listMovies or getMovie, always request at least:
    {{
      Title,
      Year,
      Rating,
      Runtime,
      Description,
      Director,
      Actors
    }}
    --- USER REQUEST ---
    User: "{user_query}"
    AI:
    """

    try:
        api_payload = {
            "model": "qwen2.5:1.5b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0}
        }
        response = requests.post(OLLAMA_API_URL, json=api_payload)
        response.raise_for_status()
        
        response_data = response.json()
        graphql_query_str = response_data['message']['content'].strip().replace("```graphql", "").replace("```", "")
        
        graphql_payload = {"query": graphql_query_str}
        success, result = graphql_sync(schema, graphql_payload, context_value=request)
        
        
        return jsonify({
            "llm_query": graphql_query_str,
            "result": result
        })

    except requests.exceptions.RequestException as e:
        print(f"Could not connect to Ollama API: {e}")
        return jsonify({"error": "Failed to connect to the Ollama service."}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
