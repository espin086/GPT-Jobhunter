import openai
import streamlit as st


openai.api_key = st.secrets["openai"]["key"]
openai.organization = st.secrets["openai"]["org"]


def generate_completion(model, prompt, temperature, max_tokens):
    """Generate a text completion using the specified model, prompt, temperature, and max_tokens."""
    completion = openai.Completion.create(
        engine=model,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        n=1,
        stop=None,
        echo=False,
    )

    message = completion.choices[0].text
    return message
