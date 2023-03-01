import os
import requests
import openai
import argparse

openai.organization = os.getenv("OPENAI_ORGANIZATION")
openai.api_key = os.getenv("OPENAI_API_KEY")


def generate_completion(model, prompt, temperature, max_tokens):
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a text completion.")
    parser.add_argument(
        "--model",
        type=str,
        default="text-davinci-003",
        help="The model to use for text completion.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="respond to a job solicitation from a recruiter",
        help="The prompt for the text completion.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.5,
        help="The temperature for the text completion.",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=200,
        help="The maximum number of tokens for the text completion.",
    )
    args = parser.parse_args()
    print(
        generate_completion(args.model, args.prompt, args.temperature, args.max_tokens)
    )
