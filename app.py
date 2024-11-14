from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import os
import pandas as pd
from collections import deque, defaultdict
from fuzzywuzzy import process # type: ignore

app = Flask(__name__)
CORS(app) 

@app.route('/')
def home():
    return "Welcome to the ASK INDIRA chatbot API! To use the chatbot, send a POST request to the /ask endpoint."


# Load stop words from a file
def load_words(file_name):
    word_set = set()
    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            word_set.add(line.strip().lower())
    return word_set

# Load categories and responses from Excel files
def load_categories(folder_path):
    categories = defaultdict(list)
    responses = {}
    more_responses = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.xlsx'):
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_excel(file_path)
            for _, row in df.iterrows():
                categories[row['category']].append(row['subcategory'])
                responses[row['subcategory']] = row['response']
                more_responses[row['subcategory']] = row.get('more', '')
    return categories, responses, more_responses

# Perform BFS to get subcategories
def bfs(categories, start_category):
    visited = set()
    queue = deque([start_category])
    result = []

    while queue:
        category = queue.popleft()
        if category not in visited:
            visited.add(category)
            result.append(category)
            for subcategory in categories[category]:
                if subcategory not in visited:
                    queue.append(subcategory)
    return result

# Get the best match for a token
def get_best_match(query, choices, threshold=80):
    if len(query) < 5:
        if query in choices:
            return query
        return None
    best_match, score = process.extractOne(query, choices)
    if score >= threshold:
        return best_match
    return None

# Process user input and respond
def process_input(input_text, stop_words, categories, responses, more_responses, question_count):
    input_text = input_text.lower()
    tokens = re.findall(r'\b\w+\b', input_text)

    found_keyword = False
    all_categories = list(categories.keys())
    all_subcategories = [subcat for subcats in categories.values() for subcat in subcats]

    for token in tokens:
        best_category_match = get_best_match(token, all_categories)
        best_subcategory_match = get_best_match(token, all_subcategories)

        if best_category_match:
            found_keyword = True
            subcategories = bfs(categories, best_category_match)
            chosen_subcategory = subcategories[0]  # Here, choose the first one or customize for user choice
            best_chosen_subcategory_match = get_best_match(chosen_subcategory, subcategories)
            if best_chosen_subcategory_match and best_chosen_subcategory_match in responses:
                question_count[best_chosen_subcategory_match] += 1
                if question_count[best_chosen_subcategory_match] > 1 and more_responses[best_chosen_subcategory_match]:
                    return more_responses[best_chosen_subcategory_match]
                else:
                    return responses[best_chosen_subcategory_match]
            else:
                return "Sorry, I don't have information on that subcategory."
        elif best_subcategory_match:
            found_keyword = True
            if best_subcategory_match in responses:
                question_count[best_subcategory_match] += 1
                if question_count[best_subcategory_match] > 1 and more_responses[best_subcategory_match]:
                    return more_responses[best_subcategory_match]
                else:
                    return responses[best_subcategory_match]
            else:
                return "Sorry, I don't have information on that subcategory."

    if not found_keyword:
        return "I am sorry, I don't have an answer for that."

# Initialize data
stop_words = load_words('C:\\Users\\shrey\\OneDrive\\Desktop\\Indira\\Indu\\ASK INDIRA\\Resources\\stopwords.txt')
folder_path = 'C:\\Users\\shrey\\OneDrive\\Desktop\\Indira\\Indu\\ASK INDIRA\\Resources'  # Adjust the path as needed
categories, responses, more_responses = load_categories(folder_path)
question_count = defaultdict(int)

# Flask route for processing input
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    user_input = data.get('input', '')
    if user_input.lower() == "bye":
        return jsonify({"response": "Goodbye!"})

    response_text = process_input(user_input, stop_words, categories, responses, more_responses, question_count)
    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True)
