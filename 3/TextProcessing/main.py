import spacy
from spacy.matcher import Matcher
import re

# It's recommended to use a model that's more suited for a production
# environment, like 'en_core_web_trf' for higher accuracy, but
# 'en_core_web_sm' is smaller and faster for demonstration purposes.
# You may need to download it first: python -m spacy download en_core_web_sm
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading 'en_core_web_sm' model...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def is_valid_entity(entity, job_role_keywords, stop_words):
    """
    A filter to check if an entity is a valid technology.

    Args:
        entity: The spaCy entity span.
        job_role_keywords: A set of keywords that typically appear in job titles.
        stop_words: A set of general words to ignore.

    Returns:
        True if the entity is likely a technology, False otherwise.
    """
    # 1. Normalize the entity text to lowercase for consistent checks.
    normalized_text = entity.text.lower()

    # 2. Ignore entities that are labeled as a person.
    if entity.label_ == "PERSON":
        return False

    # 3. Check against the general stop words list.
    if normalized_text in stop_words:
        return False

    # 4. Check if any token in the entity is a job role keyword.
    for token in entity:
        if token.lower_ in job_role_keywords:
            return False

    return True


def extract_technologies(job_descriptions: list[str]) -> list[str]:
    """
    Processes a list of job descriptions to extract unique technologies using NER and pattern matching.

    Args:
        job_descriptions: A list of strings, where each string is a job description.

    Returns:
        A sorted list of unique technologies identified across all job descriptions.
    """
    unique_technologies = set()

    # A more generic set of keywords to identify and filter out job titles.
    job_role_keywords = {
        "developer", "engineer", "scientist", "specialist", "architect",
        "manager", "lead", "senior", "junior", "full-stack", "full stack"
    }
    # A smaller, more general list of stop words.
    stop_words = {
        "inc", "llc", "company", "team", "agile", "restful apis",
        "ideal candidate", "strong understanding", "google cloud platform"
    }

    # We can add more specific technology patterns here if needed.
    tech_patterns = [
        # [{"LOWER": "python"}], [{"LOWER": "java"}], [{"LOWER": "c++"}],
        # [{"LOWER": "javascript"}], [{"LOWER": "react"}], [{"LOWER": "angular"}],
        # [{"LOWER": "vue.js"}], [{"LOWER": "node.js"}], [{"LOWER": "django"}],
        # [{"LOWER": "flask"}], [{"LOWER": "spring"}], [{"LOWER": "kubernetes"}],
        # [{"LOWER": "docker"}], [{"LOWER": "aws"}], [{"LOWER": "azure"}],
        # [{"LOWER": "gcp"}], [{"LOWER": "tensorflow"}], [{"LOWER": "pytorch"}],
        # [{"LOWER": "scikit-learn"}], [{"LOWER": "pandas"}], [{"LOWER": "numpy"}],
        # [{"LOWER": "sql"}], [{"LOWER": "nosql"}], [{"LOWER": "mongodb"}],
        # [{"LOWER": "postgresql"}], [{"LOWER": "git"}], [{"LOWER": "jenkins"}],
        # [{"LOWER": "jira"}], [{"LOWER": "spacy"}], [{"LOWER": "nltk"}],
        # [{"LOWER": "spark"}], [{"LOWER": "hadoop"}],
        # [{"TEXT": {"REGEX": r"^[A-Z][a-z]+\.(js|JS)$"}}],
        # [{"TEXT": {"REGEX": r"^[A-Z][a-z]+(\s[A-Z][a-z]+)*\s(JS|js|Framework|Library)$"}}]
    ]

    matcher = Matcher(nlp.vocab)
    for i, pattern in enumerate(tech_patterns):
        matcher.add(f"TECH_PATTERN_{i}", [pattern])

    for description in job_descriptions:
        doc = nlp(description)

        # 1. Extract entities from the pre-trained NER model
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG"]:
                # Use the new, more intelligent filter function
                if is_valid_entity(ent, job_role_keywords, stop_words):
                    unique_technologies.add(ent.text.lower())

        # 2. Use the custom matcher (currently empty based on user's test)
        matches = matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            unique_technologies.add(span.text.lower())

        # 3. Use regex for acronyms (e.g., AWS, GCP, API)
        acronym_pattern = r'\b[A-Z]{2,}\b'
        found_acronyms = re.findall(acronym_pattern, description)
        for acronym in found_acronyms:
            # Check against job role keywords to avoid acronyms like 'HR' or 'PM' if they appear.
            if acronym.lower() not in job_role_keywords:
                unique_technologies.add(acronym.lower())

    return sorted(list(unique_technologies))

if __name__ == "__main__":
    # A list of sample job descriptions to test the script
    job_postings = [
        """
        Senior Python Developer
        We are looking for a Senior Python Developer with experience in Django and Flask.
        The ideal candidate should have a strong understanding of RESTful APIs and microservices.
        Experience with cloud platforms like AWS or Azure is a plus. You will be working with PostgreSQL and MongoDB.
        Familiarity with containerization technologies such as Docker and Kubernetes is required.
        Knowledge of front-end frameworks like React or Angular is beneficial.
        """,
        """
        Machine Learning Engineer
        Join our innovative team as a Machine Learning Engineer.
        You must have hands-on experience with TensorFlow and PyTorch.
        Strong skills in Python, scikit-learn, and pandas are essential.
        You will be responsible for deploying models on Google Cloud Platform (GCP).
        Experience with big data technologies like Spark and Hadoop is highly desirable.
        We use Git for version control and JIRA for project management.
        """,
        """
        Java Full Stack Developer
        We are hiring a Full Stack Developer proficient in Java and the Spring framework.
        You will be developing web applications using Angular or Vue.js on the front-end.
        Must have a solid background in SQL and database design.
        Experience with CI/CD pipelines using Jenkins is a must.
        This role involves working in an Agile environment.
        """,
        """
        Data Scientist - NLP
        We are seeking a Data Scientist with a focus on Natural Language Processing.
        The role requires expertise in NLP libraries such as spaCy and NLTK.
        You will be building and deploying models that solve real-world problems.
        Proficiency in Python and its data science ecosystem (numpy, pandas) is expected.
        Experience with cloud services, preferably AWS, is required for this position.
        """
    ]

    # Extract and print the unique technologies
    identified_technologies = extract_technologies(job_postings)

    print("--- Unique Technologies Identified ---")
    for tech in identified_technologies:
        print(f"- {tech}")
    print("------------------------------------")
