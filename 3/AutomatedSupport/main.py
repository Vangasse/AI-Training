import re
import spacy
import random
from spacy.training.example import Example

# We load a spaCy model for its base components, but we will create new
# models specifically for text classification.
try:
    spacy.load("en_core_web_sm")
except OSError:
    print("Downloading 'en_core_web_sm' model...")
    from spacy.cli import download
    download("en_core_web_sm")


def extract_ticket_entities(ticket_text: str) -> dict:
    """
    Extracts structured entities from a ticket using regular expressions.
    This version correctly handles single-line and multi-line fields.

    Args:
        ticket_text: The full string content of a single support ticket.

    Returns:
        A dictionary containing the extracted username, OS, version, and description.
    """
    entities = {}
    # For single-line fields, we match until the end of the line.
    # The `(.*)` pattern does this by default as `.` doesn't match newlines.
    single_line_patterns = {
        "username": r"Username:\s*(.*)",
        "os": r"OS:\s*(.*)",
        "version": r"Software Version:\s*(.*)",
    }
    for key, pattern in single_line_patterns.items():
        match = re.search(pattern, ticket_text) # No DOTALL flag
        if match:
            entities[key] = match.group(1).strip()
        else:
            entities[key] = "Not Found"

    # For the multi-line description, we use re.DOTALL to allow `.` to match newlines.
    desc_pattern = r"Description:\s*(.+)"
    match = re.search(desc_pattern, ticket_text, re.DOTALL)
    if match:
        # We also strip() here to clean up any leading/trailing whitespace.
        entities["description"] = match.group(1).strip()
    else:
        entities["description"] = "Not Found"

    return entities

def train_classifier(train_data, labels):
    """
    Trains a new spaCy text classification model.

    Args:
        train_data: Data to train the model on.
        labels: The labels for the textcat component.

    Returns:
        A trained spaCy nlp object.
    """
    # Create a new blank spaCy model
    nlp = spacy.blank("en")
    # Add the textcat pipe to the model
    textcat = nlp.add_pipe("textcat")
    # Add the labels to the pipe
    for label in labels:
        textcat.add_label(label)

    # Train the model
    optimizer = nlp.begin_training()
    for i in range(10): # Number of training iterations
        random.shuffle(train_data)
        losses = {}
        for text, annotations in train_data:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            nlp.update([example], sgd=optimizer, losses=losses)
            
    return nlp

def classify_ticket(description: str, nlp_priority, nlp_category) -> (str, str):
    """
    Classifies a ticket's priority and category using trained spaCy models.

    Args:
        description: The text description of the user's issue.
        nlp_priority: The trained spaCy model for priority classification.
        nlp_category: The trained spaCy model for category classification.

    Returns:
        A tuple containing the classified (priority, category).
    """
    # Get priority prediction
    doc_priority = nlp_priority(description)
    # Get the category with the highest score
    priority = max(doc_priority.cats, key=doc_priority.cats.get)

    # Get category prediction
    doc_category = nlp_category(description)
    # Get the category with the highest score
    category = max(doc_category.cats, key=doc_category.cats.get)

    return priority, category

def process_tickets(tickets: list[str], nlp_priority, nlp_category) -> list[dict]:
    """
    Processes a list of raw ticket strings, performing extraction and classification.

    Args:
        tickets: A list where each item is the full text of a support ticket.
        nlp_priority: The trained spaCy model for priority classification.
        nlp_category: The trained spaCy model for category classification.

    Returns:
        A list of dictionaries, where each dictionary represents a fully processed ticket.
    """
    processed_list = []
    for ticket_text in tickets:
        entities = extract_ticket_entities(ticket_text)
        if entities["description"] != "Not Found":
            priority, category = classify_ticket(entities["description"], nlp_priority, nlp_category)
            entities["priority"] = priority
            entities["category"] = category
        else:
            entities["priority"] = "N/A"
            entities["category"] = "N/A"
        processed_list.append(entities)
    return processed_list


if __name__ == "__main__":
    # --- Training Data Definition ---
    # Define labels for each classification task
    PRIORITY_LABELS = ["High", "Medium", "Low"]
    CATEGORY_LABELS = ["Bug", "Feature Request", "Question", "Security"]

    # Data for Priority Classification (expanded for better generalization)
    train_data_priority = [
        ("The application has a critical error and crashes. I'm unable to work.", {"cats": {"High": 1, "Medium": 0, "Low": 0}}),
        ("The system is failing and this is urgent.", {"cats": {"High": 1, "Medium": 0, "Low": 0}}),
        ("I found a critical security vulnerability.", {"cats": {"High": 1, "Medium": 0, "Low": 0}}),
        ("The app just wiped my data. This is a catastrophe.", {"cats": {"High": 1, "Medium": 0, "Low": 0}}), # New example for data loss
        ("The new feature is very slow and shows inconsistent data.", {"cats": {"High": 0, "Medium": 1, "Low": 0}}),
        ("I'm having a problem that makes the tool difficult to use.", {"cats": {"High": 0, "Medium": 1, "Low": 0}}),
        ("The export function creates a corrupted file. It's an annoying issue.", {"cats": {"High": 0, "Medium": 1, "Low": 0}}),
        ("The layout is broken on save, making my work unusable.", {"cats": {"High": 0, "Medium": 1, "Low": 0}}), # New example for functional but broken UI
        ("I have a minor visual glitch on the main screen.", {"cats": {"High": 0, "Medium": 0, "Low": 1}}),
        ("There is a small typo in the documentation.", {"cats": {"High": 0, "Medium": 0, "Low": 1}}),
        ("It would be great if you could add a dark mode.", {"cats": {"High": 0, "Medium": 0, "Low": 1}}), 
        ("What is the maximum file size for uploads?", {"cats": {"High": 0, "Medium": 0, "Low": 1}}),
        ("A 'nice to have' feature would be CSV export.", {"cats": {"High": 0, "Medium": 0, "Low": 1}}), # New example for low-priority ideas
    ]

    # Data for Category Classification (expanded for better generalization)
    train_data_category = [
        ("The application crashes when I click the save button. This is an error.", {"cats": {"Bug": 1, "Feature Request": 0, "Question": 0, "Security": 0}}),
        ("The login doesn't work correctly.", {"cats": {"Bug": 1, "Feature Request": 0, "Question": 0, "Security": 0}}),
        ("The reporting feature is very slow and shows inconsistent data.", {"cats": {"Bug": 1, "Feature Request": 0, "Question": 0, "Security": 0}}),
        ("The application erased my files unexpectedly.", {"cats": {"Bug": 1, "Feature Request": 0, "Question": 0, "Security": 0}}), # New example for data loss bug
        ("It would be great if you could add a dark mode.", {"cats": {"Bug": 0, "Feature Request": 1, "Question": 0, "Security": 0}}),
        ("I suggest implementing a new export format.", {"cats": {"Bug": 0, "Feature Request": 1, "Question": 0, "Security": 0}}),
        ("I have an idea for a new button on the toolbar.", {"cats": {"Bug": 0, "Feature Request": 1, "Question": 0, "Security": 0}}), # New example for feature idea
        ("How do I reset my password?", {"cats": {"Bug": 0, "Feature Request": 0, "Question": 1, "Security": 0}}),
        ("Is it possible to connect to an external database?", {"cats": {"Bug": 0, "Feature Request": 0, "Question": 1, "Security": 0}}),
        ("What is the maximum file size for uploads?", {"cats": {"Bug": 0, "Feature Request": 0, "Question": 1, "Security": 0}}),
        ("I'm having trouble with the setup for an external service.", {"cats": {"Bug": 0, "Feature Request": 0, "Question": 1, "Security": 0}}), # New example for setup question
        ("I believe I have found a security vulnerability.", {"cats": {"Bug": 0, "Feature Request": 0, "Question": 0, "Security": 1}}),
    ]

    # --- Model Training ---
    print("Training classification models...")
    nlp_priority_classifier = train_classifier(train_data_priority, PRIORITY_LABELS)
    nlp_category_classifier = train_classifier(train_data_category, CATEGORY_LABELS)
    print("Models trained successfully.")

    # --- NEW TEST CASES - UNSEEN BY THE MODEL ---
    # This list contains tickets with phrasing and scenarios not present in the training data
    # to provide a true test of the model's generalization capabilities.
    sample_tickets = [
        """
        Username: hannah_s
        OS: Windows 10
        Software Version: 2.5.1
        Description: When I save my project, the text formatting gets all messed up. The alignment is wrong and some of my images disappear. I have to manually fix it every time.
        """,
        """
        Username: ian_t
        OS: macOS Monterey
        Software Version: 2.5.1
        Description: I was thinking it would be more convenient if there was a button to directly email the report instead of having to download it first. Just an idea for the future.
        """,
        """
        Username: jessica_w
        OS: Ubuntu 20.04
        Software Version: 2.4.8
        Description: The system just deleted my entire project file without any warning! All my work from the past week is gone. This is a complete disaster, I need this recovered immediately.
        """,
        """
        Username: kevin_p
        OS: Windows 11
        Software Version: 2.5.1
        Description: I'm trying to follow the tutorial for connecting to a Salesforce database, but the authentication fails. Am I using the correct API endpoint, or is there a special configuration needed for enterprise accounts?
        """
    ]

    # Process the sample tickets using the trained models
    analyzed_tickets = process_tickets(sample_tickets, nlp_priority_classifier, nlp_category_classifier)

    # Print the results in a clean format
    print("\n--- Support Ticket Analysis Results ---")
    for i, ticket in enumerate(analyzed_tickets, 1):
        print(f"\n--- Ticket #{i} ---")
        print(f"  Username: {ticket.get('username', 'N/A')}")
        print(f"  OS: {ticket.get('os', 'N/A')}")
        print(f"  Version: {ticket.get('version', 'N/A')}")
        print(f"  Description: {ticket.get('description', 'N/A')}")
        print(f"  ==> Classified Priority: {ticket.get('priority', 'N/A')}")
        print(f"  ==> Classified Category: {ticket.get('category', 'N/A')}")
    print("\n---------------------------------------")
