import re


def to_snake_case(s):
    s = re.sub(
        r"([a-z])([A-Z])", r"\1_\2", s
    )  # Insert _ between camel case transitions
    s = re.sub(r"\W+", "_", s)  # Replace non-word characters with _
    s = re.sub(r"_+", "_", s)  # Remove duplicate _
    return s.lower().strip("_")  # Convert to lowercase and remove leading/trailing _
